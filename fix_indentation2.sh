#!/bin/bash
cd /mnt/c/code/mfai_db_repos

# Function to reindent lines
reindent() {
    file=$1
    start=$2
    end=$3
    spaces=$4
    
    for i in $(seq $start $end); do
        indent=$(printf "%${spaces}s" "")
        sed -i "${i}s/^[ \t]*/$indent/" $file
    done
}

# Fix indentation for the rest of the add_repository function
reindent "mfai_db_repos/cli/commands/repositories.py" 101 149 12

# Fix the update_repository function
# First fix the Progress block
reindent "mfai_db_repos/cli/commands/repositories.py" 315 358 12

# Fix the delete_repository function
reindent "mfai_db_repos/cli/commands/repositories.py" 425 427 4

echo "Fixed additional indentation issues"