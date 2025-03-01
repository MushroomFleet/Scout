#!/usr/bin/env python3

import os
import shutil
import json
import logging
import argparse
import threading
import queue
import time
import csv
import platform
from enum import Enum
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Union, Any, Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

try:
    from tqdm import tqdm
    from colorama import init, Fore, Style
    init(autoreset=True)  # Initialize colorama
except ImportError:
    print("Required packages not found. Please run: pip install -r requirements.txt")
    exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scout.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Scout2")

# Disable verbose logging for file operations
logging.getLogger("filelock").setLevel(logging.WARNING)


class OperationMode(Enum):
    """Enum for file operation modes."""
    MOVE = "move"
    COPY = "copy"


class SortMode(Enum):
    """Enum for sorting modes."""
    NORMAL = "normal"
    DEEP = "deep"
    DEEPFREEZE = "deepfreeze"


class FileOperation:
    """Class to handle file operations (move/copy) with error handling and rollback capability."""
    
    def __init__(self, mode: OperationMode = OperationMode.MOVE):
        self.mode = mode
        self.operations_log: List[Tuple[Path, Path]] = []  # Source and destination of each operation
        self.failed_operations: List[Tuple[Path, Path, Exception]] = []
    
    def perform_operation(self, source: Path, destination: Path) -> bool:
        """Perform file operation (move or copy) based on the selected mode."""
        try:
            if self.mode == OperationMode.MOVE:
                shutil.move(str(source), str(destination))
            else:  # COPY mode
                shutil.copy2(str(source), str(destination))
            
            # Log successful operation
            self.operations_log.append((source, destination))
            return True
            
        except Exception as e:
            # Log failed operation
            self.failed_operations.append((source, destination, e))
            logger.error(f"Failed to {self.mode.value} file {source} to {destination}: {e}")
            return False
    
    def rollback(self) -> Tuple[int, int]:
        """Attempt to rollback all operations in case of failure."""
        successful_rollbacks = 0
        failed_rollbacks = 0
        
        # Only attempt rollback for move operations (copy doesn't need rollback)
        if self.mode == OperationMode.MOVE:
            # Reverse operations log to undo in reverse order
            for source, destination in reversed(self.operations_log):
                try:
                    if destination.exists():
                        shutil.move(str(destination), str(source))
                        successful_rollbacks += 1
                except Exception as e:
                    logger.error(f"Rollback failed for {destination} to {source}: {e}")
                    failed_rollbacks += 1
        
        return successful_rollbacks, failed_rollbacks


class ReportGenerator:
    """Generates reports of file organization operations."""
    
    def __init__(self, output_format: str = "console"):
        self.output_format = output_format.lower()
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
    
    def generate_report(self, 
                       files_processed: int,
                       extensions_found: Set[str],
                       moved_files: int,
                       skipped_files: int,
                       destination_path: Path,
                       operation_mode: OperationMode,
                       sort_mode: SortMode,
                       failed_operations: List[Tuple[Path, Path, Exception]] = None,
                       folders_moved: int = 0) -> str:
        """Generate a report of the organization operation."""
        self.end_time = datetime.now()
        duration = self.end_time - self.start_time
        
        # Basic report data
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration.total_seconds(),
            "operation_mode": operation_mode.value,
            "sort_mode": sort_mode.value,
            "destination_path": str(destination_path),
            "files_processed": files_processed,
            "extensions_found": len(extensions_found),
            "files_moved": moved_files,
            "files_skipped": skipped_files,
            "folders_moved": folders_moved,
            "extensions_list": sorted(list(extensions_found)),
            "failed_operations": [(str(src), str(dest), str(err)) 
                                 for src, dest, err in (failed_operations or [])]
        }
        
        # Generate report based on format
        if self.output_format == "json":
            return self._generate_json_report(report_data)
        elif self.output_format == "csv":
            return self._generate_csv_report(report_data)
        else:  # Default to console
            return self._generate_console_report(report_data)
    
    def _generate_json_report(self, report_data: Dict) -> str:
        """Generate a JSON report and save to file."""
        filename = f"scout_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        return f"Report saved to {filename}"
    
    def _generate_csv_report(self, report_data: Dict) -> str:
        """Generate a CSV report and save to file."""
        filename = f"scout_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Flatten the data for CSV
        flattened_data = {
            "Timestamp": report_data["timestamp"],
            "Duration (seconds)": report_data["duration_seconds"],
            "Operation Mode": report_data["operation_mode"],
            "Sort Mode": report_data["sort_mode"],
            "Destination Path": report_data["destination_path"],
            "Files Processed": report_data["files_processed"],
            "Extensions Found": report_data["extensions_found"],
            "Files Moved/Copied": report_data["files_moved"],
            "Folders Moved/Copied": report_data["folders_moved"],
            "Files Skipped": report_data["files_skipped"],
            "Extensions": ", ".join(report_data["extensions_list"]),
            "Failed Operations": len(report_data["failed_operations"])
        }
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=flattened_data.keys())
            writer.writeheader()
            writer.writerow(flattened_data)
            
            # Add failed operations as additional rows if any
            if report_data["failed_operations"]:
                writer.writerow({})  # Empty row
                failed_header = {
                    "Timestamp": "Source",
                    "Duration (seconds)": "Destination",
                    "Operation Mode": "Error"
                }
                writer.writerow(failed_header)
                
                for src, dest, err in report_data["failed_operations"]:
                    writer.writerow({
                        "Timestamp": src,
                        "Duration (seconds)": dest,
                        "Operation Mode": err
                    })
        
        return f"Report saved to {filename}"
    
    def _generate_console_report(self, report_data: Dict) -> str:
        """Generate a console-friendly report string."""
        operation_word = "moved" if report_data["operation_mode"] == "move" else "copied"
        
        report = [
            f"\n{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}",
            f"{Fore.CYAN}{'=' * 15} SCOUT2 SUMMARY REPORT {'=' * 15}{Style.RESET_ALL}",
            f"{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}",
            f"",
            f"{Fore.YELLOW}Operation Details:{Style.RESET_ALL}",
            f"  {Fore.WHITE}Time completed:{Style.RESET_ALL} {report_data['timestamp']}",
            f"  {Fore.WHITE}Duration:{Style.RESET_ALL} {report_data['duration_seconds']:.2f} seconds",
            f"  {Fore.WHITE}Mode:{Style.RESET_ALL} {report_data['operation_mode'].upper()}",
            f"  {Fore.WHITE}Sort Mode:{Style.RESET_ALL} {report_data['sort_mode'].upper()}",
            f"  {Fore.WHITE}Destination:{Style.RESET_ALL} {report_data['destination_path']}",
            f"",
            f"{Fore.YELLOW}Results:{Style.RESET_ALL}",
            f"  {Fore.GREEN}✓ Files processed:{Style.RESET_ALL} {report_data['files_processed']}",
            f"  {Fore.GREEN}✓ Unique extensions found:{Style.RESET_ALL} {report_data['extensions_found']}",
            f"  {Fore.GREEN}✓ Files successfully {operation_word}:{Style.RESET_ALL} {report_data['files_moved']}",
        ]
        
        # Add folders moved in DeepFreeze mode
        if report_data["folders_moved"] > 0:
            report.append(f"  {Fore.GREEN}✓ Folders {operation_word}:{Style.RESET_ALL} {report_data['folders_moved']}")
        
        if report_data["files_skipped"] > 0:
            report.append(f"  {Fore.RED}✗ Files skipped:{Style.RESET_ALL} {report_data['files_skipped']}")
        
        if report_data["failed_operations"]:
            report.append(f"  {Fore.RED}✗ Failed operations:{Style.RESET_ALL} {len(report_data['failed_operations'])}")
        
        report.extend([
            f"",
            f"{Fore.YELLOW}Extensions organized:{Style.RESET_ALL}",
            f"  {', '.join(report_data['extensions_list'])}",
        ])
        
        if report_data["failed_operations"]:
            report.extend([
                f"",
                f"{Fore.RED}Failed Operations:{Style.RESET_ALL}"
            ])
            
            for src, dest, err in report_data["failed_operations"][:5]:  # Show max 5 failures
                report.append(f"  {Fore.RED}✗{Style.RESET_ALL} {src} → {dest}: {err}")
                
            if len(report_data["failed_operations"]) > 5:
                report.append(f"  ... and {len(report_data['failed_operations']) - 5} more")
                
            report.append(f"  See log file for complete details.")
        
        report.extend([
            f"",
            f"{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}",
            f"{Fore.GREEN}File organization complete!{Style.RESET_ALL}"
        ])
        
        return "\n".join(report)


class UIManager:
    """Manages user interface components and interactions."""
    
    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors
        if not self.use_colors:
            # Disable colorama if colors are not wanted
            global Fore, Style
            Fore.GREEN = Fore.RED = Fore.YELLOW = Fore.CYAN = Fore.WHITE = ""
            Style.RESET_ALL = ""
    
    def get_path_input(self, prompt: str, check_exists: bool = True) -> Path:
        """Get a valid path from user input with colored prompts."""
        while True:
            path_str = input(f"{Fore.CYAN}{prompt}{Style.RESET_ALL} ")
            path = Path(path_str)
            
            if check_exists and not path.exists():
                print(f"{Fore.RED}Error: Path '{path}' does not exist.{Style.RESET_ALL}")
                continue
                
            if check_exists and not path.is_dir():
                print(f"{Fore.RED}Error: Path '{path}' is not a directory.{Style.RESET_ALL}")
                continue
                
            return path
    
    def get_confirmation(self, message: str, default: bool = False) -> bool:
        """Get confirmation from user with colored prompt."""
        default_prompt = "[Y/n]" if default else "[y/N]"
        response = input(f"{Fore.YELLOW}{message} {default_prompt}{Style.RESET_ALL} ").strip().lower()
        
        if not response:
            return default
            
        return response[0] == 'y'
    
    def get_operation_mode(self) -> OperationMode:
        """Prompt user to select operation mode."""
        print(f"\n{Fore.CYAN}Select operation mode:{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}1){Style.RESET_ALL} Move files (files will be removed from source)")
        print(f"  {Fore.YELLOW}2){Style.RESET_ALL} Copy files (files will remain in source)")
        
        while True:
            choice = input(f"{Fore.CYAN}Enter your choice [1-2] (default: 1):{Style.RESET_ALL} ").strip()
            
            if not choice:
                return OperationMode.MOVE
                
            if choice == "1":
                return OperationMode.MOVE
            elif choice == "2":
                return OperationMode.COPY
            else:
                print(f"{Fore.RED}Invalid choice. Please enter 1 or 2.{Style.RESET_ALL}")
    
    def get_report_format(self) -> str:
        """Prompt user to select report format."""
        print(f"\n{Fore.CYAN}Select report format:{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}1){Style.RESET_ALL} Console (display in terminal)")
        print(f"  {Fore.YELLOW}2){Style.RESET_ALL} JSON (save to file)")
        print(f"  {Fore.YELLOW}3){Style.RESET_ALL} CSV (save to file)")
        
        while True:
            choice = input(f"{Fore.CYAN}Enter your choice [1-3] (default: 1):{Style.RESET_ALL} ").strip()
            
            if not choice or choice == "1":
                return "console"
            elif choice == "2":
                return "json"
            elif choice == "3":
                return "csv"
            else:
                print(f"{Fore.RED}Invalid choice. Please enter 1, 2, or 3.{Style.RESET_ALL}")
    
    def get_sort_mode(self) -> SortMode:
        """Prompt user to select sort mode."""
        print(f"\n{Fore.CYAN}Select sort mode:{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}1){Style.RESET_ALL} Normal (organize files in the source directory only)")
        print(f"  {Fore.YELLOW}2){Style.RESET_ALL} DeepSort (recursively organize files in all subdirectories)")
        print(f"  {Fore.YELLOW}3){Style.RESET_ALL} DeepFreeze (organize files and move subdirectories to '_Folders')")
        
        while True:
            choice = input(f"{Fore.CYAN}Enter your choice [1-3] (default: 1):{Style.RESET_ALL} ").strip()
            
            if not choice or choice == "1":
                return SortMode.NORMAL
            elif choice == "2":
                return SortMode.DEEP
            elif choice == "3":
                return SortMode.DEEPFREEZE
            else:
                print(f"{Fore.RED}Invalid choice. Please enter 1, 2, or 3.{Style.RESET_ALL}")
    
    def create_progress_bar(self, total: int, desc: str) -> tqdm:
        """Create a tqdm progress bar with appropriate styling."""
        return tqdm(
            total=total,
            desc=f"{Fore.CYAN}{desc}{Style.RESET_ALL}",
            unit="file",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
        )
    
    def print_welcome(self) -> None:
        """Print welcome message."""
        scout_art = r"""
 _____                 _   ___  
/  ___|               | | |__ \ 
\ `--.  ___ ___  _   _| |_   ) |
 `--. \/ __/ _ \| | | | __|  / / 
/\__/ / (_| (_) | |_| | |_  / /_ 
\____/ \___\___/ \__,_|\__||____|
        """
        
        print(f"{Fore.CYAN}{scout_art}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'=' * 50}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Scout2 File Organizer - Organize files by extension{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{'=' * 50}{Style.RESET_ALL}")


class ScoutConfig:
    """Manages configuration loading and saving."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("scout_config.json")
        self.config: Dict[str, Any] = self._get_default_config()
        
        # Load config if exists
        if self.config_path.exists():
            try:
                self._load_config()
            except Exception as e:
                logger.warning(f"Failed to load config from {self.config_path}: {e}")
                logger.info("Using default configuration")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration settings."""
        return {
            "last_target_path": str(Path.home()),
            "last_destination_path": str(Path.home() / "Organized"),
            "operation_mode": OperationMode.MOVE.value,
            "sort_mode": SortMode.NORMAL.value,
            "report_format": "console",
            "use_colors": True
        }
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        with open(self.config_path, 'r') as f:
            loaded_config = json.load(f)
            self.config.update(loaded_config)
    
    def save_config(self, 
                   target_path: Path, 
                   destination_path: Path,
                   operation_mode: OperationMode,
                   sort_mode: SortMode,
                   report_format: str) -> None:
        """Save current configuration to file."""
        self.config.update({
            "last_target_path": str(target_path),
            "last_destination_path": str(destination_path),
            "operation_mode": operation_mode.value,
            "sort_mode": sort_mode.value,
            "report_format": report_format
        })
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
                
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    def get_last_target_path(self) -> Path:
        """Get last used target path."""
        return Path(self.config.get("last_target_path", str(Path.home())))
    
    def get_last_destination_path(self) -> Path:
        """Get last used destination path."""
        return Path(self.config.get("last_destination_path", str(Path.home() / "Organized")))
    
    def get_operation_mode(self) -> OperationMode:
        """Get preferred operation mode."""
        mode_str = self.config.get("operation_mode", OperationMode.MOVE.value)
        return OperationMode.MOVE if mode_str == "move" else OperationMode.COPY
    
    def get_report_format(self) -> str:
        """Get preferred report format."""
        return self.config.get("report_format", "console")
    
    def get_use_colors(self) -> bool:
        """Get color usage preference."""
        return self.config.get("use_colors", True)
    
    def get_sort_mode(self) -> SortMode:
        """Get preferred sort mode."""
        mode_str = self.config.get("sort_mode", SortMode.NORMAL.value)
        if mode_str == "deep":
            return SortMode.DEEP
        elif mode_str == "deepfreeze":
            return SortMode.DEEPFREEZE
        else:
            return SortMode.NORMAL


class FileOrganizer:
    """Main file organizer class that handles the organization process."""
    
    def __init__(self, ui_manager: UIManager, config: ScoutConfig):
        self.ui_manager = ui_manager
        self.config = config
        self.file_op = FileOperation()
        self.report_generator = ReportGenerator()
        
        # Initialize counters and trackers
        self.files_processed = 0
        self.extensions_found: Set[str] = set()
        self.moved_files = 0
        self.skipped_files = 0
        
        # Worker queue and threading
        self.work_queue: queue.Queue = queue.Queue()
        self.worker_count = min(32, (os.cpu_count() or 4) * 2)  # 2x CPU cores, max 32
        self.completion_event = threading.Event()
    
    def get_files_from_target(self, target_path: Path, sort_mode: SortMode = SortMode.NORMAL) -> List[Path]:
        """Get a list of files from the target path, with optional recursive scanning."""
        files = []
        subdirs_processed = 0
        
        try:
            if sort_mode == SortMode.DEEP:
                # Recursively walk through all subdirectories
                for root, dirs, filenames in os.walk(target_path):
                    subdirs_processed += len(dirs)
                    root_path = Path(root)
                    for filename in filenames:
                        files.append(root_path / filename)
                
                logger.info(f"Found {len(files)} files in {target_path} and {subdirs_processed} subdirectories")
            else:
                # Only consider files in the root directory, ignore subdirectories
                for item in os.listdir(target_path):
                    item_path = target_path / item
                    if item_path.is_file():
                        files.append(item_path)
                        
                logger.info(f"Found {len(files)} files in {target_path}")
        except Exception as e:
            logger.error(f"Error accessing target directory: {e}")
            raise
            
        return files
        
    def process_deepfreeze_folders(self, source_path: Path, destination_path: Path) -> int:
        """
        Process folders in DeepFreeze mode by moving them to a '_Folders' directory.
        
        Args:
            source_path: The source directory path
            destination_path: The destination directory path
            
        Returns:
            Number of directories processed
        """
        # Create the _Folders directory in the destination
        folders_dir = destination_path / "_Folders"
        os.makedirs(folders_dir, exist_ok=True)
        
        folders_moved = 0
        
        # Find all immediate subdirectories in the source
        for item in os.listdir(source_path):
            item_path = source_path / item
            
            if item_path.is_dir():
                # Determine destination folder path
                dest_folder = folders_dir / item
                
                # Handle duplicate folder names
                counter = 1
                original_name = item
                while dest_folder.exists():
                    new_name = f"{original_name}_{counter}"
                    dest_folder = folders_dir / new_name
                    counter += 1
                
                try:
                    # Move the folder and its contents
                    if self.file_op.mode == OperationMode.MOVE:
                        shutil.move(str(item_path), str(dest_folder))
                    else:  # COPY mode
                        shutil.copytree(str(item_path), str(dest_folder))
                    
                    # Log operation
                    self.file_op.operations_log.append((item_path, dest_folder))
                    
                    folders_moved += 1
                    logger.info(f"Successfully {self.file_op.mode.value}d folder {item_path} to {dest_folder}")
                    
                except Exception as e:
                    logger.error(f"Failed to {self.file_op.mode.value} folder {item_path} to {dest_folder}: {e}")
                    self.file_op.failed_operations.append((item_path, dest_folder, e))
        
        logger.info(f"{self.file_op.mode.value.capitalize()}d {folders_moved} folders to {folders_dir}")
        return folders_moved
    
    def get_file_extensions(self, files: List[Path]) -> Set[str]:
        """Extract unique file extensions from a list of files."""
        extensions = set()
        
        for file in files:
            # Get extension without the dot and convert to lowercase
            ext = file.suffix[1:].lower() if file.suffix else "no_extension"
            extensions.add(ext)
            
        logger.info(f"Found {len(extensions)} unique file extensions")
        return extensions
    
    def create_extension_directories(self, destination_path: Path, extensions: Set[str]) -> Dict[str, Path]:
        """Create directories for each file extension."""
        created_dirs = {}
        
        with self.ui_manager.create_progress_bar(len(extensions), "Creating directories") as pbar:
            for ext in extensions:
                dir_path = destination_path / ext
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    created_dirs[ext] = dir_path
                except Exception as e:
                    logger.error(f"Error creating directory {dir_path}: {e}")
                pbar.update(1)
        
        return created_dirs
    
    def _process_file(self, file: Path, ext_dir: Path) -> Tuple[bool, Optional[Path]]:
        """Process a single file (worker function)."""
        try:
            # Normalize extension
            ext = file.suffix[1:].lower() if file.suffix else "no_extension"
            
            # Generate destination path
            dest_file = ext_dir / file.name
            
            # Handle name conflicts
            counter = 1
            original_stem = file.stem
            while dest_file.exists():
                new_name = f"{original_stem}_{counter}{file.suffix}"
                dest_file = ext_dir / new_name
                counter += 1
                
            # Perform the file operation
            success = self.file_op.perform_operation(file, dest_file)
            
            return success, dest_file
            
        except Exception as e:
            logger.error(f"Error processing file {file}: {e}")
            return False, None
    
    def worker(self, pbar: tqdm) -> None:
        """Worker thread for processing files."""
        while not self.completion_event.is_set():
            try:
                # Get item from queue with timeout
                item = self.work_queue.get(timeout=0.5)
                
                # Process the item
                file, ext_dir = item
                success, _ = self._process_file(file, ext_dir)
                
                # Update counters
                with threading.Lock():
                    if success:
                        self.moved_files += 1
                    else:
                        self.skipped_files += 1
                
                # Update progress bar
                pbar.update(1)
                
                # Mark task as done
                self.work_queue.task_done()
                
            except queue.Empty:
                # Queue is empty, nothing to do
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")
                with threading.Lock():
                    self.skipped_files += 1
    
    def process_files(self, files: List[Path], extension_dirs: Dict[str, Path]) -> Tuple[int, int]:
        """Process files using a thread pool and work queue."""
        # Reset counters
        self.moved_files = 0
        self.skipped_files = 0
        self.completion_event.clear()
        
        # Create progress bar
        operation_name = "Moving" if self.file_op.mode == OperationMode.MOVE else "Copying"
        pbar = self.ui_manager.create_progress_bar(len(files), f"{operation_name} files")
        
        try:
            # Start worker threads
            workers = []
            for _ in range(self.worker_count):
                thread = threading.Thread(target=self.worker, args=(pbar,), daemon=True)
                thread.start()
                workers.append(thread)
            
            # Queue up all files for processing
            for file in files:
                ext = file.suffix[1:].lower() if file.suffix else "no_extension"
                
                # Skip if directory for this extension wasn't created
                if ext not in extension_dirs:
                    logger.warning(f"No directory for extension '{ext}', skipping {file.name}")
                    self.skipped_files += 1
                    pbar.update(1)
                    continue
                    
                # Add to processing queue
                self.work_queue.put((file, extension_dirs[ext]))
            
            # Wait for completion
            self.work_queue.join()
            
        finally:
            # Signal threads to exit and wait for them
            self.completion_event.set()
            for thread in workers:
                thread.join(timeout=1.0)
                
            # Close progress bar
            pbar.close()
        
        return self.moved_files, self.skipped_files
    
    def run(self, target_path: Path, destination_path: Path, operation_mode: OperationMode,
           sort_mode: SortMode, report_format: str) -> None:
        """Run the file organization process."""
        try:
            # Set operation mode and report format
            self.file_op.mode = operation_mode
            self.report_generator = ReportGenerator(output_format=report_format)
            
            # Get files from target directory
            files = self.get_files_from_target(target_path, sort_mode)
            
            if not files:
                print(f"{Fore.YELLOW}No files found in the target directory.{Style.RESET_ALL}")
                return
                
            self.files_processed = len(files)
            print(f"{Fore.GREEN}Found {len(files)} files to organize.{Style.RESET_ALL}")
            
            # Get unique file extensions
            self.extensions_found = self.get_file_extensions(files)
            print(f"{Fore.GREEN}Found {len(self.extensions_found)} unique file extensions.{Style.RESET_ALL}")
            
            # Create directories for each extension
            extension_dirs = self.create_extension_directories(destination_path, self.extensions_found)
            
            # Confirm destructive operations
            if operation_mode == OperationMode.MOVE and self.files_processed > 0:
                confirm = self.ui_manager.get_confirmation(
                    f"You are about to move {self.files_processed} files from {target_path} to {destination_path}. Proceed?",
                    default=False
                )
                if not confirm:
                    print(f"{Fore.YELLOW}Operation cancelled by user.{Style.RESET_ALL}")
                    return
            
            # Process files
            moved_files, skipped_files = self.process_files(files, extension_dirs)
            
            # Process folders if in DeepFreeze mode
            folders_moved = 0
            if sort_mode == SortMode.DEEPFREEZE:
                print(f"{Fore.GREEN}Processing folders in DeepFreeze mode...{Style.RESET_ALL}")
                folders_moved = self.process_deepfreeze_folders(target_path, destination_path)
                if folders_moved > 0:
                    print(f"{Fore.GREEN}Successfully {self.file_op.mode.value}d {folders_moved} folders to {destination_path / '_Folders'}{Style.RESET_ALL}")
            
            # Generate and display report
            report = self.report_generator.generate_report(
                files_processed=self.files_processed,
                extensions_found=self.extensions_found,
                moved_files=moved_files,
                skipped_files=skipped_files,
                destination_path=destination_path,
                operation_mode=operation_mode,
                sort_mode=sort_mode,
                failed_operations=self.file_op.failed_operations,
                folders_moved=folders_moved
            )
            
            print(report)
            
            # Save config for next time
            self.config.save_config(
                target_path=target_path,
                destination_path=destination_path,
                operation_mode=operation_mode,
                sort_mode=sort_mode,
                report_format=report_format
            )
            
        except Exception as e:
            logger.error(f"Organization process failed: {e}")
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
            
            # Try to rollback if in move mode
            if operation_mode == OperationMode.MOVE and self.file_op.operations_log:
                print(f"{Fore.YELLOW}Attempting to rollback file moves...{Style.RESET_ALL}")
                success, failed = self.file_op.rollback()
                print(f"{Fore.GREEN}Successfully rolled back {success} operations.{Style.RESET_ALL}")
                if failed > 0:
                    print(f"{Fore.RED}Failed to roll back {failed} operations.{Style.RESET_ALL}")
                    print(f"{Fore.RED}Some files may remain in the destination directory.{Style.RESET_ALL}")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Scout2 File Organizer - Organize files by extension.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-s", "--source", 
        dest="source_path",
        help="Source directory path containing files to organize"
    )
    
    parser.add_argument(
        "-d", "--destination", 
        dest="destination_path",
        help="Destination directory where organized files will be placed"
    )
    
    parser.add_argument(
        "-m", "--mode",
        dest="operation_mode",
        choices=["move", "copy"],
        default="move",
        help="Operation mode: 'move' files or 'copy' files"
    )
    
    parser.add_argument(
        "-r", "--report",
        dest="report_format",
        choices=["console", "json", "csv"],
        default="console",
        help="Report format after completion"
    )
    
    parser.add_argument(
        "-c", "--config",
        dest="config_path",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--no-color",
        dest="no_color",
        action="store_true",
        default=False,
        help="Disable colored output"
    )
    
    parser.add_argument(
        "--no-confirm",
        dest="no_confirm",
        action="store_true",
        default=False,
        help="Skip confirmation prompts"
    )
    
    parser.add_argument(
        "--deep-sort",
        dest="deep_sort",
        action="store_true",
        default=False,
        help="Enable DeepSort mode to recursively scan subdirectories"
    )
    
    parser.add_argument(
        "--deep-freeze",
        dest="deep_freeze",
        action="store_true",
        default=False,
        help="Enable DeepFreeze mode to organize files and move subdirectories to '_Folders'"
    )
    
    return parser.parse_args()


def main() -> None:
    """Main entry point for the Scout2 file organizer."""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Set up configuration
    config_path = Path(args.config_path) if args.config_path else None
    config = ScoutConfig(config_path)
    
    # Set up UI manager
    use_colors = not args.no_color and config.get_use_colors()
    ui_manager = UIManager(use_colors=use_colors)
    
    # Welcome message
    ui_manager.print_welcome()
    
    try:
        # Get source and destination paths
        if args.source_path:
            source_path = Path(args.source_path)
            if not source_path.exists() or not source_path.is_dir():
                print(f"{Fore.RED}Error: Source path '{source_path}' does not exist or is not a directory.{Style.RESET_ALL}")
                return
        else:
            default_source = config.get_last_target_path()
            print(f"{Fore.CYAN}Default source path: {default_source}{Style.RESET_ALL}")
            source_path = ui_manager.get_path_input("Enter source directory path:", check_exists=True)
        
        if args.destination_path:
            destination_path = Path(args.destination_path)
        else:
            default_dest = config.get_last_destination_path()
            print(f"{Fore.CYAN}Default destination path: {default_dest}{Style.RESET_ALL}")
            destination_path = ui_manager.get_path_input("Enter destination directory path:", check_exists=False)
        
        # Create destination directory if it doesn't exist
        try:
            os.makedirs(destination_path, exist_ok=True)
        except Exception as e:
            print(f"{Fore.RED}Error creating destination directory: {e}{Style.RESET_ALL}")
            return
        
        # Get operation mode
        if args.operation_mode:
            operation_mode = OperationMode.MOVE if args.operation_mode == "move" else OperationMode.COPY
        else:
            operation_mode = ui_manager.get_operation_mode()
        
        # Get report format
        if args.report_format:
            report_format = args.report_format
        else:
            report_format = ui_manager.get_report_format()
        
        # Get sort mode
        if args.deep_freeze:
            sort_mode = SortMode.DEEPFREEZE
        elif args.deep_sort:
            sort_mode = SortMode.DEEP
        else:
            sort_mode = ui_manager.get_sort_mode()
        
        # Create and run the file organizer
        organizer = FileOrganizer(ui_manager, config)
        organizer.run(source_path, destination_path, operation_mode, sort_mode, report_format)
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operation cancelled by user.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
        logger.exception("Unhandled exception in main function")


if __name__ == "__main__":
    main()
