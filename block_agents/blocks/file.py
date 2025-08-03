"""File handling blocks for the block-based agentic pipeline system."""

import csv
import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Set

import yaml

from block_agents.core.block import Block
from block_agents.core.context import Context
from block_agents.core.errors import InputValidationError
from block_agents.core.registry import register_block


@register_block("input_file")
class InputFileBlock(Block):
    """Block for reading and parsing files.
    
    This block allows users to read files of various formats:
    - Text files
    - JSON files
    - CSV files
    - YAML files
    """

    def __init__(self, block_id: str, config: Dict[str, Any]):
        """Initialize a new InputFileBlock.

        Args:
            block_id: Unique identifier for this block instance
            config: Block configuration
        """
        super().__init__(block_id, config)
        
        # Get file options from config
        self.file_path = config.get("file_path", "")
        self.file_format = config.get("file_format", "auto")  # auto, text, json, csv, yaml
        self.encoding = config.get("encoding", "utf-8")
        self.csv_options = config.get("csv_options", {})

    def get_uploaded_file_path(self, digest: str) -> Optional[str]:
        """Find the path to an uploaded file by its SHA256 digest.

        Args:
            digest: SHA256 hex digest of the file

        Returns:
            Absolute path to the file if found, else None
        """
        upload_dir = self.config.get("storage", '')

        for fname in os.listdir(upload_dir):
            fpath = os.path.join(upload_dir, fname)
            if os.path.isfile(fpath):
                with open(fpath, "rb") as f:
                    file_digest = hashlib.sha256(f.read()).hexdigest()
                if file_digest == digest:
                    return os.path.abspath(fpath)
        return None
        
    def process(self, inputs: Dict[str, Any], context: Context) -> Dict[str, Any]:
        """Process the inputs and produce an output.

        Args:
            inputs: Input values for the block
            context: Execution context

        Returns:
            Dictionary containing the file content
        """
        # Get file path from inputs or config
        file_path = self.get_uploaded_file_path(inputs.get("digest", self.file_path))
        if not file_path:
            raise InputValidationError(
                "File path not provided in inputs or config",
                block_id=self.id,
            )

        
        # Determine format if auto
        file_format = self.file_format
        if file_format == "auto":
            file_format = self._detect_format(file_path)
            
        # Log the operation
        context.log(self.id, f"Reading file: {file_path} as {file_format}")
        
        # Read and parse the file
        if file_format == "text":
            content = self._read_text_file(file_path)
            result = {"text": content}
        elif file_format == "json":
            content = self._read_json_file(file_path)
            result = {"data": content}
        elif file_format == "csv":
            content = self._read_csv_file(file_path)
            result = {"data": content}
        elif file_format == "yaml":
            content = self._read_yaml_file(file_path)
            result = {"data": content}
        else:
            # Default to text
            content = self._read_text_file(file_path)
            result = {"text": content}
            
        # Log success
        context.log(self.id, f"Successfully read file: {file_path}")
        
        return result
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate the inputs to the block.

        Args:
            inputs: Input values for the block

        Raises:
            InputValidationError: If validation fails
        """
        # File path can come from inputs or config
        file_path = inputs.get("file_path", self.file_path)
        
        if not file_path:
            raise InputValidationError(
                "File path not provided in inputs or config",
                block_id=self.id,
            )
            
        if not os.path.exists(file_path):
            raise InputValidationError(
                f"File does not exist: {file_path}",
                block_id=self.id,
            )
            
        if not os.path.isfile(file_path):
            raise InputValidationError(
                f"Path is not a file: {file_path}",
                block_id=self.id,
            )
            
    def get_required_inputs(self) -> Set[str]:
        """Get the set of required input keys for this block.

        Returns:
            Set of required input keys
        """
        # File path can come from config
        return set() if self.file_path else {"file_path"}

    def get_optional_inputs(self) -> Set[str]:
        """Get the set of optional input keys for this block.

        Returns:
            Set of optional input keys
        """
        # File path can come from inputs even if it's in config
        return {"file_path"} if self.file_path else set()
        
    def _detect_format(self, file_path: str) -> str:
        """Detect the file format from the file extension.

        Args:
            file_path: Path to the file

        Returns:
            Detected format string
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext == ".json":
            return "json"
        elif ext == ".csv":
            return "csv"
        elif ext in (".yaml", ".yml"):
            return "yaml"
        else:
            return "text"
            
    def _read_text_file(self, file_path: str) -> str:
        """Read a text file.

        Args:
            file_path: Path to the file

        Returns:
            File content as string
        """
        with open(file_path, encoding=self.encoding) as f:
            return f.read()
            
    def _read_json_file(self, file_path: str) -> Any:
        """Read a JSON file.

        Args:
            file_path: Path to the file

        Returns:
            Parsed JSON content
        """
        with open(file_path, encoding=self.encoding) as f:
            return json.load(f)
            
    def _read_csv_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Read a CSV file.

        Args:
            file_path: Path to the file

        Returns:
            List of dictionaries representing CSV rows
        """
        # Get CSV options from config
        delimiter = self.csv_options.get("delimiter", ",")
        quotechar = self.csv_options.get("quotechar", '"')
        has_header = self.csv_options.get("has_header", True)
        
        with open(file_path, encoding=self.encoding, newline="") as f:
            if has_header:
                reader = csv.DictReader(f, delimiter=delimiter, quotechar=quotechar)
                return list(reader)
            else:
                reader = csv.reader(f, delimiter=delimiter, quotechar=quotechar)
                rows = list(reader)
                return [{"row": row} for row in rows]
                
    def _read_yaml_file(self, file_path: str) -> Any:
        """Read a YAML file.

        Args:
            file_path: Path to the file

        Returns:
            Parsed YAML content
        """
        with open(file_path, encoding=self.encoding) as f:
            return yaml.safe_load(f)



@register_block("file_writer")
class FileWriterBlock(Block):
    """Block for writing data to files.
    
    This block allows users to write data to files in various formats:
    - Text files
    - JSON files
    - CSV files
    - YAML files
    """

    def __init__(self, block_id: str, config: Dict[str, Any]):
        """Initialize a new FileWriterBlock.

        Args:
            block_id: Unique identifier for this block instance
            config: Block configuration
        """
        super().__init__(block_id, config)
        
        # Get file options from config
        self.file_path = config.get("file_path", "")
        self.file_format = config.get("file_format", "auto")  # auto, text, json, csv, yaml
        self.encoding = config.get("encoding", "utf-8")
        self.overwrite = config.get("overwrite", True)
        self.csv_options = config.get("csv_options", {})
        self.json_options = config.get("json_options", {"indent": 2})
        
    def process(self, inputs: Dict[str, Any], context: Context) -> Dict[str, str]:
        """Process the inputs and produce an output.

        Args:
            inputs: Input values for the block
            context: Execution context

        Returns:
            Dictionary containing the file path
        """
        # Get file path from inputs or config
        file_path = inputs.get("file_path", self.file_path)
        
        # Get data to write
        data = inputs.get("data")
        text = inputs.get("text")
        
        # Check if file exists and we're not overwriting
        if os.path.exists(file_path) and not self.overwrite:
            context.log(self.id, f"File exists and overwrite=False: {file_path}")
            return {"file_path": file_path}
            
        # Determine format if auto
        file_format = self.file_format
        if file_format == "auto":
            file_format = self._detect_format(file_path)
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
        # Log the operation
        context.log(self.id, f"Writing to file: {file_path} as {file_format}")
        
        # Write the file
        if file_format == "text":
            self._write_text_file(file_path, text or str(data))
        elif file_format == "json":
            self._write_json_file(file_path, data)
        elif file_format == "csv":
            self._write_csv_file(file_path, data)
        elif file_format == "yaml":
            self._write_yaml_file(file_path, data)
        else:
            # Default to text
            self._write_text_file(file_path, text or str(data))
            
        # Log success
        context.log(self.id, f"Successfully wrote to file: {file_path}")
        
        return {"file_path": file_path}
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate the inputs to the block.

        Args:
            inputs: Input values for the block

        Raises:
            InputValidationError: If validation fails
        """
        # File path can come from inputs or config
        file_path = inputs.get("file_path", self.file_path)
        
        if not file_path:
            raise InputValidationError(
                "File path not provided in inputs or config",
                block_id=self.id,
            )
            
        # Either data or text must be provided
        if "data" not in inputs and "text" not in inputs:
            raise InputValidationError(
                "Neither 'data' nor 'text' provided in inputs",
                block_id=self.id,
            )
            
    def get_required_inputs(self) -> Set[str]:
        """Get the set of required input keys for this block.

        Returns:
            Set of required input keys
        """
        # Either data or text must be provided
        return set() if self.file_path else {"file_path"}

    def get_optional_inputs(self) -> Set[str]:
        """Get the set of optional input keys for this block.

        Returns:
            Set of optional input keys
        """
        # File path can be overridden
        optional = {"text", "data"}
        if self.file_path:
            optional.add("file_path")
        return optional
        
    def _detect_format(self, file_path: str) -> str:
        """Detect the file format from the file extension.

        Args:
            file_path: Path to the file

        Returns:
            Detected format string
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext == ".json":
            return "json"
        elif ext == ".csv":
            return "csv"
        elif ext in (".yaml", ".yml"):
            return "yaml"
        else:
            return "text"
            
    def _write_text_file(self, file_path: str, content: str) -> None:
        """Write a text file.

        Args:
            file_path: Path to the file
            content: Content to write
        """
        with open(file_path, "w", encoding=self.encoding) as f:
            f.write(content)
            
    def _write_json_file(self, file_path: str, data: Any) -> None:
        """Write a JSON file.

        Args:
            file_path: Path to the file
            data: Data to write
        """
        with open(file_path, "w", encoding=self.encoding) as f:
            json.dump(data, f, **self.json_options)
            
    def _write_csv_file(self, file_path: str, data: List[Dict[str, Any]]) -> None:
        """Write a CSV file.

        Args:
            file_path: Path to the file
            data: Data to write (list of dictionaries)
        """
        # Get CSV options from config
        delimiter = self.csv_options.get("delimiter", ",")
        quotechar = self.csv_options.get("quotechar", '"')
        
        with open(file_path, "w", encoding=self.encoding, newline="") as f:
            if data:
                writer = csv.DictWriter(
                    f, 
                    fieldnames=data[0].keys(), 
                    delimiter=delimiter, 
                    quotechar=quotechar
                )
                writer.writeheader()
                writer.writerows(data)
                
    def _write_yaml_file(self, file_path: str, data: Any) -> None:
        """Write a YAML file.

        Args:
            file_path: Path to the file
            data: Data to write
        """
        with open(file_path, "w", encoding=self.encoding) as f:
            yaml.dump(data, f)