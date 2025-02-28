#!/usr/bin/env python3

import os
import shutil
from pathlib import Path
from tqdm import tqdm
import sys

def create_directory(directory_path):
    """Create directory if it doesn't exist."""
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {directory_path}: {e}")
        return False

def get_valid_path(prompt, check_exists=True):
    """Get a valid path from user input."""
    while True:
        path_str = input(prompt)
        path = Path(path_str)
        
        if check_exists and not path.exists():
            print(f"Error: Path '{path}' does not exist.")
            continue
            
        if check_exists and not path.is_dir():
            print(f"Error: Path '{path}' is not a directory.")
            continue
            
        return path

def get_files_from_target(target_path):
    """Get a list of files (not directories) from the target path."""
    files = []
    
    try:
        # Only consider files in the root directory, ignore subdirectories
        for item in os.listdir(target_path):
            item_path = Path(target_path) / item
            if item_path.is_file():
                files.append(item_path)
    except Exception as e:
        print(f"Error accessing target directory: {e}")
        sys.exit(1)
        
    return files

def get_file_extensions(files):
    """Extract unique file extensions from a list of files."""
    extensions = set()
    
    for file in files:
        # Get extension without the dot and convert to lowercase
        ext = file.suffix[1:].lower() if file.suffix else "no_extension"
        extensions.add(ext)
        
    return extensions

def create_extension_directories(destination_path, extensions):
    """Create directories for each file extension."""
    created_dirs = {}
    
    print("Creating extension directories...")
    for ext in tqdm(extensions, desc="Creating directories"):
        dir_path = Path(destination_path) / ext
        if create_directory(dir_path):
            created_dirs[ext] = dir_path
        
    return created_dirs

def move_files(files, extension_dirs, destination_path):
    """Move files to their respective extension directories."""
    moved_files = 0
    skipped_files = 0
    
    print("Moving files...")
    for file in tqdm(files, desc="Moving files"):
        try:
            # Get extension without the dot and convert to lowercase
            ext = file.suffix[1:].lower() if file.suffix else "no_extension"
            
            # Skip if directory for this extension wasn't created
            if ext not in extension_dirs:
                print(f"Warning: No directory for extension '{ext}', skipping {file.name}")
                skipped_files += 1
                continue
                
            dest_file = extension_dirs[ext] / file.name
            
            # Handle name conflicts
            counter = 1
            original_stem = file.stem
            while dest_file.exists():
                new_name = f"{original_stem}_{counter}{file.suffix}"
                dest_file = extension_dirs[ext] / new_name
                counter += 1
                
            # Move the file
            shutil.move(str(file), str(dest_file))
            moved_files += 1
            
        except Exception as e:
            print(f"Error moving file {file}: {e}")
            skipped_files += 1
            
    return moved_files, skipped_files

def main():
    print("=== Scout File Organizer ===")
    print("This tool will organize files by extension from a source directory to a destination directory.")
    
    # Get target and destination paths
    target_path = get_valid_path("Enter target directory path: ", check_exists=True)
    destination_path = get_valid_path("Enter destination directory path: ", check_exists=False)
    
    # Create destination directory if it doesn't exist
    if not create_directory(destination_path):
        print("Failed to create destination directory. Exiting.")
        sys.exit(1)
    
    # Get files from target directory
    files = get_files_from_target(target_path)
    
    if not files:
        print("No files found in the target directory.")
        sys.exit(0)
        
    print(f"Found {len(files)} files to organize.")
    
    # Get unique file extensions
    extensions = get_file_extensions(files)
    print(f"Found {len(extensions)} unique file extensions.")
    
    # Create directories for each extension
    extension_dirs = create_extension_directories(destination_path, extensions)
    
    # Move files to their respective directories
    moved_files, skipped_files = move_files(files, extension_dirs, destination_path)
    
    # Print summary
    print("\n=== Summary ===")
    print(f"Total files processed: {len(files)}")
    print(f"Files successfully moved: {moved_files}")
    print(f"Files skipped: {skipped_files}")
    print(f"Extensions organized: {len(extension_dirs)}")
    print("\nFile organization complete!")

if __name__ == "__main__":
    main()
