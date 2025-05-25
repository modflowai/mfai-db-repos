"""
Batch processing utilities for embedding generation.
Provides tools for efficient parallel processing of embedding tasks.
"""
import asyncio
import time
from dataclasses import dataclass
from typing import Callable, Dict, Generic, List, Optional, TypeVar, Union

from mfai_db_repos.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')  # Input type
R = TypeVar('R')  # Result type


@dataclass
class BatchProcessingResult(Generic[T, R]):
    """Results from batch processing operation."""
    
    successful: List[R]  # Successfully processed results
    failed: List[T]  # Failed inputs
    errors: Dict[int, Exception]  # Errors by input index
    
    @property
    def success_count(self) -> int:
        """Get the number of successful operations."""
        return len(self.successful)
    
    @property
    def failure_count(self) -> int:
        """Get the number of failed operations."""
        return len(self.failed)
    
    @property
    def total_count(self) -> int:
        """Get the total number of operations."""
        return self.success_count + self.failure_count


class BatchProcessor(Generic[T, R]):
    """Processor for handling batches of items in parallel."""
    
    def __init__(
        self,
        process_func: Callable[[T], R] | Callable[[T], asyncio.Future[R]],
        max_concurrency: int = 5,
        batch_size: int = 20,
        rate_limit_per_minute: Optional[int] = None,
        is_async: bool = True,
    ):
        """Initialize the batch processor.
        
        Args:
            process_func: Function that processes a single item
            max_concurrency: Maximum number of concurrent tasks
            batch_size: Number of items in a batch
            rate_limit_per_minute: Optional rate limit
            is_async: Whether the process function is async
        """
        self.process_func = process_func
        self.max_concurrency = max_concurrency
        self.batch_size = batch_size
        self.rate_limit_per_minute = rate_limit_per_minute
        self.is_async = is_async
        
        # Rate limiting state
        self.request_count = 0
        self.last_reset = time.time()
        
        logger.info(
            f"BatchProcessor initialized with concurrency={max_concurrency}, "
            f"batch_size={batch_size}, rate_limit={rate_limit_per_minute}"
        )
    
    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        if not self.rate_limit_per_minute:
            return
            
        current_time = time.time()
        time_passed = current_time - self.last_reset
        
        # Reset counter if a minute has passed
        if time_passed > 60:
            self.request_count = 0
            self.last_reset = current_time
            return
        
        # Check if we've hit the rate limit
        if self.request_count >= self.rate_limit_per_minute:
            # Calculate sleep time needed to respect rate limit
            sleep_time = 60 - time_passed
            logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)
            self.request_count = 0
            self.last_reset = time.time()
    
    async def _process_item(self, item: T, index: int) -> tuple[int, Union[R, Exception]]:
        """Process a single item and return the result with its index.
        
        Args:
            item: Item to process
            index: Index of the item in the original list
            
        Returns:
            Tuple of (index, result or exception)
        """
        try:
            await self._check_rate_limit()
            if self.rate_limit_per_minute:
                self.request_count += 1
                
            if self.is_async:
                result = await self.process_func(item)
            else:
                # Run synchronous function in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self.process_func, item)
                
            return index, result
        except Exception as e:
            logger.error(f"Error processing item {index}: {str(e)}")
            return index, e
    
    async def process_batch(self, items: List[T]) -> BatchProcessingResult[T, R]:
        """Process a batch of items with concurrency control.
        
        Args:
            items: List of items to process
            
        Returns:
            BatchProcessingResult with successful and failed items
        """
        if not items:
            return BatchProcessingResult(successful=[], failed=[], errors={})
        
        # Create semaphore to control concurrency
        semaphore = asyncio.Semaphore(self.max_concurrency)
        
        async def process_with_semaphore(item, index):
            async with semaphore:
                return await self._process_item(item, index)
        
        # Create tasks for all items
        tasks = [process_with_semaphore(item, i) for i, item in enumerate(items)]
        results = await asyncio.gather(*tasks)
        
        # Separate successful results from errors
        successful = []
        failed = []
        errors = {}
        
        for index, result in results:
            if isinstance(result, Exception):
                failed.append(items[index])
                errors[index] = result
            else:
                successful.append(result)
        
        return BatchProcessingResult(
            successful=successful,
            failed=failed,
            errors=errors,
        )
    
    async def process_all(
        self, 
        items: List[T],
        show_progress: bool = True
    ) -> BatchProcessingResult[T, R]:
        """Process all items in batches.
        
        Args:
            items: List of items to process
            show_progress: Whether to log progress
            
        Returns:
            BatchProcessingResult with successful and failed items
        """
        if not items:
            return BatchProcessingResult(successful=[], failed=[], errors={})
        
        # Split items into batches
        batches = [items[i:i + self.batch_size] for i in range(0, len(items), self.batch_size)]
        
        # Track all results
        all_successful = []
        all_failed = []
        all_errors = {}
        
        for i, batch in enumerate(batches):
            if show_progress:
                logger.info(f"Processing batch {i+1}/{len(batches)} ({len(batch)} items)")
                
            # Process the batch
            result = await self.process_batch(batch)
            
            # Accumulate results
            all_successful.extend(result.successful)
            all_failed.extend(result.failed)
            
            # Update error indices to match original position
            batch_start = i * self.batch_size
            for error_idx, error in result.errors.items():
                all_errors[batch_start + error_idx] = error
            
            if show_progress:
                logger.info(
                    f"Batch {i+1} completed: {result.success_count} succeeded, "
                    f"{result.failure_count} failed"
                )
        
        if show_progress:
            logger.info(
                f"All processing completed: {len(all_successful)} succeeded, "
                f"{len(all_failed)} failed, {len(items)} total"
            )
        
        return BatchProcessingResult(
            successful=all_successful,
            failed=all_failed,
            errors=all_errors,
        )