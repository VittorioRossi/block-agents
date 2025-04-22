"""Tests for script execution blocks."""

import os
import tempfile
from typing import Any, Dict

import pytest

from block_agents.blocks.script import CScriptBlock, PythonScriptBlock
from block_agents.core.context import Context
from block_agents.core.errors import BlockRuntimeError, InputValidationError


class TestPythonScriptBlock:
    """Tests for the PythonScriptBlock."""

    def test_init(self):
        """Test that the block initializes correctly."""
        block = PythonScriptBlock("test_block", {"script": "print('Hello')"})
        assert block.id == "test_block"
        assert block.script == "print('Hello')"
        assert block.script_file == ""
        assert block.python_path == "python"
        assert block.timeout_seconds == 60
        assert block.capture_stdout is True
        assert block.capture_stderr is True
        
    def test_execute_script_string(self, mocker):
        """Test executing a script from a string."""
        # Create a script
        script = "print('Hello, world!')"
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block
        block = PythonScriptBlock("test_block", {})
        
        # Process the script
        result = block.process({"script": script}, mock_context)
        
        # Check the result
        assert "stdout" in result
        assert "Hello, world!" in result["stdout"]
        assert "success" in result
        assert result["success"] is True
        assert result["return_code"] == 0
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_execute_script_file(self, mocker):
        """Test executing a script from a file."""
        # Create a script file
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".py") as f:
            f.write("print('Hello from file!')")
            script_file = f.name
            
        try:
            # Create a mock context
            mock_context = mocker.MagicMock(spec=Context)
            
            # Create the block
            block = PythonScriptBlock("test_block", {})
            
            # Process the script
            result = block.process({"script_file": script_file}, mock_context)
            
            # Check the result
            assert "stdout" in result
            assert "Hello from file!" in result["stdout"]
            assert "success" in result
            assert result["success"] is True
            assert result["return_code"] == 0
            
            # Verify logging
            mock_context.log.assert_called()
        finally:
            # Clean up
            os.remove(script_file)
            
    def test_execute_with_error(self, mocker):
        """Test executing a script that raises an error."""
        # Create a script with an error
        script = "print(undefined_variable)"
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block
        block = PythonScriptBlock("test_block", {})
        
        # Process the script
        result = block.process({"script": script}, mock_context)
        
        # Check the result
        assert "stderr" in result
        assert "NameError" in result["stderr"]
        assert "success" in result
        assert result["success"] is False
        assert result["return_code"] != 0
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_validate_inputs_missing_script(self, mocker):
        """Test validation with missing script."""
        # Create the block
        block = PythonScriptBlock("test_block", {})
        
        # Validate empty inputs
        with pytest.raises(InputValidationError):
            block.validate_inputs({})
            
    def test_validate_inputs_nonexistent_file(self, mocker):
        """Test validation with nonexistent script file."""
        # Create the block
        block = PythonScriptBlock("test_block", {})
        
        # Validate with nonexistent file
        with pytest.raises(InputValidationError):
            block.validate_inputs({"script_file": "/nonexistent/script.py"})
            
    def test_script_timeout(self, mocker):
        """Test script timeout."""
        # Create a script that will timeout
        script = "import time; time.sleep(10)"
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block with a short timeout
        block = PythonScriptBlock("test_block", {"timeout_seconds": 0.1})
        
        # Process the script with expected timeout
        with pytest.raises(BlockRuntimeError) as exc_info:
            block.process({"script": script}, mock_context)
            
        # Verify the error message
        assert "timed out" in str(exc_info.value)
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_get_required_inputs(self):
        """Test getting required inputs."""
        # With script in config
        block1 = PythonScriptBlock("test_block", {"script": "print('Hello')"})
        assert block1.get_required_inputs() == set()
        
        # Without script in config
        block2 = PythonScriptBlock("test_block", {})
        assert block2.get_required_inputs() == {"script"}
        
    def test_get_optional_inputs(self):
        """Test getting optional inputs."""
        # With script in config
        block1 = PythonScriptBlock("test_block", {"script": "print('Hello')"})
        assert "script" not in block1.get_optional_inputs()
        assert "script_file" in block1.get_optional_inputs()
        
        # Without script in config
        block2 = PythonScriptBlock("test_block", {})
        assert "script" in block2.get_optional_inputs()
        assert "script_file" in block2.get_optional_inputs()


class TestCScriptBlock:
    """Tests for the CScriptBlock."""

    def test_init(self):
        """Test that the block initializes correctly."""
        block = CScriptBlock("test_block", {"script": "#include <stdio.h>\nint main() { printf(\"Hello\"); return 0; }"})
        assert block.id == "test_block"
        assert block.script == "#include <stdio.h>\nint main() { printf(\"Hello\"); return 0; }"
        assert block.script_file == ""
        assert block.compiler == "gcc"
        assert block.compiler_flags == ["-Wall"]
        assert block.timeout_seconds == 60
        assert block.capture_stdout is True
        assert block.capture_stderr is True
        
    def test_execute_script_string(self, mocker):
        """Test executing a script from a string."""
        # Create a C script
        script = """
        #include <stdio.h>
        int main() {
            printf("Hello, world!\\n");
            return 0;
        }
        """
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block
        block = CScriptBlock("test_block", {})
        
        # Process the script
        result = block.process({"script": script}, mock_context)
        
        # Check the result
        assert "stdout" in result
        assert "Hello, world!" in result["stdout"]
        assert "success" in result
        assert result["success"] is True
        assert result["return_code"] == 0
        assert result["stage"] == "execution"
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_execute_script_file(self, mocker):
        """Test executing a script from a file."""
        # Create a C script file
        with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".c") as f:
            f.write("""
            #include <stdio.h>
            int main() {
                printf("Hello from file!\\n");
                return 0;
            }
            """)
            script_file = f.name
            
        try:
            # Create a mock context
            mock_context = mocker.MagicMock(spec=Context)
            
            # Create the block
            block = CScriptBlock("test_block", {})
            
            # Process the script
            result = block.process({"script_file": script_file}, mock_context)
            
            # Check the result
            assert "stdout" in result
            assert "Hello from file!" in result["stdout"]
            assert "success" in result
            assert result["success"] is True
            assert result["return_code"] == 0
            assert result["stage"] == "execution"
            
            # Verify logging
            mock_context.log.assert_called()
        finally:
            # Clean up
            os.remove(script_file)
            
    def test_execute_with_compilation_error(self, mocker):
        """Test executing a script with a compilation error."""
        # Create a script with a compilation error
        script = """
        #include <stdio.h>
        int main() {
            printf("Hello, world!\\n")  // Missing semicolon
            return 0;
        }
        """
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block
        block = CScriptBlock("test_block", {})
        
        # Process the script
        result = block.process({"script": script}, mock_context)
        
        # Check the result
        assert "stderr" in result
        assert "error" in result["stderr"].lower()
        assert "success" in result
        assert result["success"] is False
        assert result["return_code"] != 0
        assert result["stage"] == "compilation"
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_execute_with_runtime_error(self, mocker):
        """Test executing a script with a runtime error."""
        # Create a script with a runtime error
        script = """
        #include <stdio.h>
        int main() {
            int x = 5;
            int y = 0;
            printf("%d\\n", x / y);  // Division by zero
            return 0;
        }
        """
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block
        block = CScriptBlock("test_block", {})
        
        # Process the script
        result = block.process({"script": script}, mock_context)
        
        # The behavior here depends on the platform, might terminate with signal or return error
        assert result["stage"] == "execution"
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_execute_with_args(self, mocker):
        """Test executing a script with arguments."""
        # Create a C script that uses arguments
        script = """
        #include <stdio.h>
        int main(int argc, char *argv[]) {
            printf("Argument count: %d\\n", argc);
            for (int i = 0; i < argc; i++) {
                printf("Arg %d: %s\\n", i, argv[i]);
            }
            return 0;
        }
        """
        
        # Create a mock context
        mock_context = mocker.MagicMock(spec=Context)
        
        # Create the block
        block = CScriptBlock("test_block", {})
        
        # Process the script with arguments
        result = block.process({
            "script": script,
            "args": ["arg1", "arg2", "arg3"]
        }, mock_context)
        
        # Check the result
        assert "stdout" in result
        assert "Argument count: 4" in result["stdout"]  # program name + 3 args
        assert "Arg 1: arg1" in result["stdout"]
        assert "Arg 2: arg2" in result["stdout"]
        assert "Arg 3: arg3" in result["stdout"]
        assert "success" in result
        assert result["success"] is True
        assert result["return_code"] == 0
        
        # Verify logging
        mock_context.log.assert_called()
        
    def test_validate_inputs_missing_script(self, mocker):
        """Test validation with missing script."""
        # Create the block
        block = CScriptBlock("test_block", {})
        
        # Validate empty inputs
        with pytest.raises(InputValidationError):
            block.validate_inputs({})
            
    def test_validate_inputs_nonexistent_file(self, mocker):
        """Test validation with nonexistent script file."""
        # Create the block
        block = CScriptBlock("test_block", {})
        
        # Validate with nonexistent file
        with pytest.raises(InputValidationError):
            block.validate_inputs({"script_file": "/nonexistent/script.c"})
            
    def test_validate_inputs_invalid_args(self, mocker):
        """Test validation with invalid arguments."""
        # Create the block
        block = CScriptBlock("test_block", {})
        
        # Validate with non-list args
        with pytest.raises(InputValidationError):
            block.validate_inputs({
                "script": "#include <stdio.h>\nint main() { return 0; }",
                "args": "not a list"
            })
            
    def test_get_required_inputs(self):
        """Test getting required inputs."""
        # With script in config
        block1 = CScriptBlock("test_block", {"script": "#include <stdio.h>\nint main() { return 0; }"})
        assert block1.get_required_inputs() == set()
        
        # Without script in config
        block2 = CScriptBlock("test_block", {})
        assert block2.get_required_inputs() == {"script"}
        
    def test_get_optional_inputs(self):
        """Test getting optional inputs."""
        # With script in config
        block1 = CScriptBlock("test_block", {"script": "#include <stdio.h>\nint main() { return 0; }"})
        assert "script" not in block1.get_optional_inputs()
        assert "script_file" in block1.get_optional_inputs()
        assert "args" in block1.get_optional_inputs()
        
        # Without script in config
        block2 = CScriptBlock("test_block", {})
        assert "script" in block2.get_optional_inputs()
        assert "script_file" in block2.get_optional_inputs()
        assert "args" in block2.get_optional_inputs()