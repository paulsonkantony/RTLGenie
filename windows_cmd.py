import subprocess
import os

import logging
logger = logging.getLogger("root")
logger.info("Imported Windows Command module")

def run_cmd_command(command_string, print_output=True):
    """
    Runs a command in the Windows Command Prompt (cmd.exe) and captures its output.

    Args:
        command_string (str): The full command string to execute (e.g., "dir", "ipconfig /all").
        print_output (bool): If True, prints stdout and stderr to the console.

    Returns:
        dict: A dictionary containing:
            'success' (bool): True if the command executed successfully (exit code 0).
            'stdout' (str): The standard output from the command.
            'stderr' (str): The standard error from the command.
            'returncode' (int): The exit code of the command.
            'error_message' (str): An error message if an exception occurred.
    """
    result = {
        'success': False,
        'stdout': '',
        'stderr': '',
        'returncode': None,
        'error_message': None
    }

    try:
        logger.info(f"\n--- Executing command: {command_string} ---")
        # Use shell=True for CMD built-in commands or complex command strings
        # that rely on shell features (like pipes, redirection, environment variables).
        process = subprocess.run(
            command_string,
            shell=True,
            capture_output=True,
            text=True,           # Decodes stdout/stderr as text using default encoding
            check=False          # Do not raise an exception for non-zero exit codes here
                                 # We'll handle it manually by checking returncode
        )

        result['stdout'] = process.stdout
        result['stderr'] = process.stderr
        result['returncode'] = process.returncode
        result['success'] = (process.returncode == 0)

        logger.debug("\n--- STDOUT ---")
        logger.debug(result['stdout'].strip())
        logger.debug("\n--- STDERR ---")
        logger.debug(result['stderr'].strip())

        if not result['success']:
            logger.error(f"\nCommand failed with exit code: {result['returncode']}")
        else:
            logger.info("\nCommand executed successfully.")

    except FileNotFoundError:
        result['error_message'] = f"Error: Command '{command_string.split()[0]}' not found. Make sure it's a valid executable or command."
        logger.error(result['error_message'])
    except Exception as e:
        result['error_message'] = f"An unexpected error occurred: {e}"
        logger.exception(result['error_message'])

    return result

# --- Example Usage ---
if __name__ == "__main__":

    # --- Example 1: Simple 'dir' command (success) ---
    print("\n--- Running 'dir' command ---")
    dir_result = run_cmd_command("dir")
    print(f"\nSummary: Success={dir_result['success']}, ReturnCode={dir_result['returncode']}")
    # You can access specific parts:
    # print(dir_result['stdout'])

    # --- Example 2: 'ipconfig /all' (success, network info) ---
    print("\n--- Running 'ipconfig /all' command ---")
    ipconfig_result = run_cmd_command("ipconfig /all")
    print(f"\nSummary: Success={ipconfig_result['success']}, ReturnCode={ipconfig_result['returncode']}")

    # --- Example 3: Command that does not exist (failure) ---
    print("\n--- Running non-existent command ---")
    non_existent_result = run_cmd_command("thiscommanddoesnotexist123")
    print(f"\nSummary: Success={non_existent_result['success']}, ReturnCode={non_existent_result['returncode']}")
    if non_existent_result['stderr']:
        print(f"Error output: {non_existent_result['stderr'].strip()}")

    # --- Example 4: 'echo' command (success, basic output) ---
    print("\n--- Running 'echo' command ---")
    echo_result = run_cmd_command("echo Hello from Python!")
    print(f"\nSummary: Success={echo_result['success']}, ReturnCode={echo_result['returncode']}")

    # --- Example 5: Command with arguments and potential errors (pinging a non-existent host) ---
    print("\n--- Running 'ping' command with a non-existent host ---")
    ping_result = run_cmd_command("ping no.such.host.example.com")
    print(f"\nSummary: Success={ping_result['success']}, ReturnCode={ping_result['returncode']}")
    # ping returns non-zero if host is unreachable, so success will be False.
    if ping_result['success']:
        print("Ping successful!")
    else:
        print("Ping failed or host unreachable.")
        if "could not find host" in ping_result['stdout'].lower(): # Ping often prints errors to stdout
            print("Specific error: Host not found.")

    # --- Example 6: Changing directory and listing contents (CMD built-in with chaining) ---
    # Note: 'cd' itself only changes the directory for the *current* cmd.exe instance
    # launched by subprocess. It won't affect the Python script's working directory.
    # To list files in a specific directory, it's better to pass the path directly to dir:
    print("\n--- Running 'dir' on a specific directory ---")
    target_dir = os.path.expanduser("~") # User's home directory
    if os.path.exists(target_dir):
        dir_specific_result = run_cmd_command(f"dir \"{target_dir}\"")
        print(f"\nSummary: Success={dir_specific_result['success']}, ReturnCode={dir_specific_result['returncode']}")
    else:
        print(f"Directory {target_dir} does not exist.")

    # --- Example 7: Creating a dummy file and then typing its content ---
    dummy_file = "test_output.txt"
    with open(dummy_file, "w") as f:
        f.write("This is a test line.\nAnother line here.")
    print(f"\n--- Running 'type {dummy_file}' ---")
    type_result = run_cmd_command(f"type {dummy_file}")
    print(f"\nSummary: Success={type_result['success']}, ReturnCode={type_result['returncode']}")

    # Clean up dummy file
    if os.path.exists(dummy_file):
        os.remove(dummy_file)
