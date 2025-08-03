"""Script execution blocks for the block-based agentic pipeline system."""

import os
import subprocess
import tempfile
from typing import Any, Dict, Set

from block_agents.core.block import Block
from block_agents.core.context import Context
from block_agents.core.errors import BlockRuntimeError, InputValidationError
from block_agents.core.registry import register_block


@register_block("python_script")
class PythonScriptBlock(Block):
    """Block for executing Python scripts.
    
    This block allows users to execute Python code either provided directly as a string
    or from a file, with input data provided as variables to the script.
    """

    def __init__(self, block_id: str, config: Dict[str, Any]):
        """Initialize a new PythonScriptBlock.

        Args:
            block_id: Unique identifier for this block instance
            config: Block configuration
        """
        super().__init__(block_id, config)
        
        # Get script options from config
        self.script = config.get("code", "")
        self.script_file = config.get("script_file", "")
        self.python_path = config.get("python_path", "python")
        self.timeout_seconds = config.get("timeout_seconds", 60)
        self.capture_stdout = config.get("capture_stdout", True)
        self.capture_stderr = config.get("capture_stderr", True)
        self.return_vars = config.get("return_vars", [])
        
    def process(self, inputs: Dict[str, Any], context: Context) -> Dict[str, Any]:
        """Process the inputs and produce an output.

        Args:
            inputs: Input values for the block
            context: Execution context

        Returns:
            Dictionary containing the script results
        """
        # Get script from inputs or config
        script = inputs.get("script", self.script)
        script_file = inputs.get("script_file", self.script_file)
        
        # Create a temporary file for the script if needed
        if script and not script_file:
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
                f.write(script)
                script_file = f.name
        
        # Prepare environment variables
        env = os.environ.copy()
        
        # Add inputs as environment variables
        for key, value in inputs.items():
            if isinstance(value, (str, int, float, bool)):
                env[f"BLOCK_INPUT_{key.upper()}"] = str(value)
        
        # Log the execution
        context.log(self.id, f"Executing Python script: {script_file}")
        
        try:
            # Execute the script
            # TODO: Add security checks when needed - currently ignoring S603 for subprocess execution
            process = subprocess.Popen(  # noqa: S603
                [self.python_path, script_file],
                stdout=subprocess.PIPE if self.capture_stdout else None,
                stderr=subprocess.PIPE if self.capture_stderr else None,
                env=env,
                text=True
            ) 
            
            # Wait for completion with timeout
            stdout, stderr = process.communicate(timeout=self.timeout_seconds)
            
            # Prepare result
            result = {}
            
            if self.capture_stdout:
                result["stdout"] = stdout
                
            if self.capture_stderr:
                result["stderr"] = stderr
                
            # Check return code
            if process.returncode != 0:
                context.log(self.id, f"Script execution failed with return code: {process.returncode}")
                result["success"] = False
                result["return_code"] = process.returncode
            else:
                context.log(self.id, "Script execution completed successfully")
                result["success"] = True
                result["return_code"] = 0
                
            return result
            
        except subprocess.TimeoutExpired as e:
            context.log(self.id, f"Script execution timed out after {self.timeout_seconds} seconds")
            raise BlockRuntimeError(
                f"Script execution timed out after {self.timeout_seconds} seconds",
                block_id=self.id,
            ) from e
        except Exception as e:
            context.log(self.id, f"Script execution failed: {str(e)}")
            raise BlockRuntimeError(
                f"Script execution failed: {str(e)}",
                block_id=self.id,
                details={"error": str(e)},
            ) from e
        finally:
            # Clean up temporary file if we created one
            if script and not self.script_file and os.path.exists(script_file):
                os.remove(script_file)
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate the inputs to the block.

        Args:
            inputs: Input values for the block

        Raises:
            InputValidationError: If validation fails
        """
        # Either script or script_file must be provided in inputs or config
        #script = inputs.get("script", self.script)
        #script_file = inputs.get("script_file", self.script_file)
        #
        #if not script and not script_file:
        #    raise InputValidationError(
        #        "Neither 'script' nor 'script_file' provided in inputs or config",
        #        block_id=self.id,
        #    )
        #    
        ## If script_file is provided, check that it exists
        #if script_file and not os.path.exists(script_file):
        #    raise InputValidationError(
        #        f"Script file does not exist: {script_file}",
        #        block_id=self.id,
        #    )
        return
            
    def get_required_inputs(self) -> Set[str]:
        """Get the set of required input keys for this block.

        Returns:
            Set of required input keys
        """
        # Script can come from config
        if self.script or self.script_file:
            return set()
        return {"script"}  # At least one of script or script_file is required

    def get_optional_inputs(self) -> Set[str]:
        """Get the set of optional input keys for this block.

        Returns:
            Set of optional input keys
        """
        # All inputs are optional
        optional = set()
        if not self.script:
            optional.add("script")
        if not self.script_file:
            optional.add("script_file")
        return optional


@register_block("c_script")
class CScriptBlock(Block):
    """Block for executing C scripts.
    
    This block allows users to compile and execute C code either provided directly as a string
    or from a file, with input data provided as command-line arguments.
    """

    def __init__(self, block_id: str, config: Dict[str, Any]):
        """Initialize a new CScriptBlock.

        Args:
            block_id: Unique identifier for this block instance
            config: Block configuration
        """
        super().__init__(block_id, config)
        
        # Get script options from config
        self.script: str = config.get("script", "")
        self.script_file: str = config.get("script_file", "")
        self.compiler: str = config.get("compiler", "gcc")
        self.compiler_flags: list[str] = config.get("compiler_flags", ["-Wall"])
        self.timeout_seconds: int = config.get("timeout_seconds", 60)
        self.capture_stdout: bool = config.get("capture_stdout", True)
        self.capture_stderr: bool = config.get("capture_stderr", True)
        self.args: list[str] = config.get("args", [])
        
    def process(self, inputs: Dict[str, Any], context: Context) -> Dict[str, Any]:
        """Process the inputs and produce an output.

        Args:
            inputs: Input values for the block
            context: Execution context

        Returns:
            Dictionary containing the script results
        """
        # Get script from inputs or config
        script: str = inputs.get("script", self.script)
        script_file: str = inputs.get("script_file", self.script_file)
        
        # Create a temporary directory for compilation
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create temporary files
            if script and not script_file:
                script_file = os.path.join(temp_dir, "script.c")
                with open(script_file, "w") as f:
                    f.write(script)
            
            # Output executable path
            executable = os.path.join(temp_dir, "a.out")
            
            # Compile the script
            context.log(self.id, f"Compiling C script: {script_file}")
            
            try:
                # Build the compilation command
                compile_cmd = [self.compiler, script_file, "-o", executable]
                compile_cmd.extend(self.compiler_flags)
                
                # Execute compilation
                # TODO: Add security checks when needed - currently ignoring S603 for subprocess execution
                compile_process = subprocess.run(  # noqa: S603, UP022
                    compile_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=self.timeout_seconds
                ) 

                # Check if compilation succeeded
                if compile_process.returncode != 0:
                    context.log(self.id, f"Compilation failed: {compile_process.stderr}")
                    return {
                        "success": False,
                        "stdout": compile_process.stdout,
                        "stderr": compile_process.stderr,
                        "return_code": compile_process.returncode,
                        "stage": "compilation"
                    }
                
                # Get command line arguments
                args = inputs.get("args", self.args)
                
                # Execute the compiled program
                context.log(self.id, "Executing compiled C program")
                
                run_cmd = [executable]
                if args:
                    run_cmd.extend([str(arg) for arg in args])
                
                run_process = subprocess.run( # noqa: S603, UP022
                    run_cmd,
                    stdout=subprocess.PIPE if self.capture_stdout else None,
                    stderr=subprocess.PIPE if self.capture_stderr else None,
                    text=True,
                    timeout=self.timeout_seconds
                )
                
                # Prepare result
                result = {
                    "success": run_process.returncode == 0,
                    "return_code": run_process.returncode,
                    "stage": "execution"
                }
                
                if self.capture_stdout:
                    result["stdout"] = run_process.stdout
                    
                if self.capture_stderr:
                    result["stderr"] = run_process.stderr
                
                # Log completion
                if run_process.returncode == 0:
                    context.log(self.id, "C program execution completed successfully")
                else:
                    context.log(self.id, f"C program execution failed with return code: {run_process.returncode}")
                
                return result
                
            except subprocess.TimeoutExpired:
                context.log(self.id, f"Script execution timed out after {self.timeout_seconds} seconds")
                raise BlockRuntimeError(
                    f"Script execution timed out after {self.timeout_seconds} seconds",
                    block_id=self.id,
                )
            except Exception as e:
                context.log(self.id, f"Script execution failed: {str(e)}")
                raise BlockRuntimeError(
                    f"Script execution failed: {str(e)}",
                    block_id=self.id,
                    details={"error": str(e)},
                )
        
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """Validate the inputs to the block.

        Args:
            inputs: Input values for the block

        Raises:
            InputValidationError: If validation fails
        """
        # Either script or script_file must be provided in inputs or config
        script = inputs.get("script", self.script)
        script_file = inputs.get("script_file", self.script_file)
        
        if not script and not script_file:
            raise InputValidationError(
                "Neither 'script' nor 'script_file' provided in inputs or config",
                block_id=self.id,
            )
            
        # If script_file is provided, check that it exists
        if script_file and not os.path.exists(script_file):
            raise InputValidationError(
                f"Script file does not exist: {script_file}",
                block_id=self.id,
            )
            
        # If args is provided, check that it's a list
        if "args" in inputs and not isinstance(inputs["args"], list):
            raise InputValidationError(
                "Input 'args' must be a list",
                block_id=self.id,
                details={"input_type": type(inputs["args"]).__name__},
            )
            
    def get_required_inputs(self) -> Set[str]:
        """Get the set of required input keys for this block.

        Returns:
            Set of required input keys
        """
        # Script can come from config
        if self.script or self.script_file:
            return set()
        return {"script"}  # At least one of script or script_file is required

    def get_optional_inputs(self) -> Set[str]:
        """Get the set of optional input keys for this block.

        Returns:
            Set of optional input keys
        """
        # All inputs are optional
        optional = {"args"}
        if not self.script:
            optional.add("script")
        if not self.script_file:
            optional.add("script_file")
        return optional