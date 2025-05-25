#!/bin/bash
cd /mnt/c/code/mfai_db_repos

# Fix indentation issues in repositories.py
sed -E -i '306s/^(\s+)with/        with/' mfai_db_repos/cli/commands/repositories.py
sed -E -i '307s/^(\s+)SpinnerColumn/            SpinnerColumn/' mfai_db_repos/cli/commands/repositories.py
sed -E -i '308s/^(\s+)TextColumn/            TextColumn/' mfai_db_repos/cli/commands/repositories.py
sed -E -i '309s/^(\s+)BarColumn/            BarColumn/' mfai_db_repos/cli/commands/repositories.py
sed -E -i '310s/^(\s+)TextColumn/            TextColumn/' mfai_db_repos/cli/commands/repositories.py
sed -E -i '311s/^(\s+)TimeElapsedColumn/            TimeElapsedColumn/' mfai_db_repos/cli/commands/repositories.py
sed -E -i '312s/^(\s+)console/            console/' mfai_db_repos/cli/commands/repositories.py
sed -E -i '313s/^(\s+)\)/            )/' mfai_db_repos/cli/commands/repositories.py

# Fix indentation for all lines of the Progress block
for i in $(seq 314 358); do
    sed -E -i "${i}s/^(\s+)(.+)/        \2/" mfai_db_repos/cli/commands/repositories.py
done

# Fix the delete repository function too
sed -E -i '392s/^(\s+)async with get_session/        session = await get_session/' mfai_db_repos/cli/commands/repositories.py
for i in $(seq 393 417); do
    sed -E -i "${i}s/^(\s+)(.+)/        \2/" mfai_db_repos/cli/commands/repositories.py
done

echo "Fixed indentation issues in repositories.py"