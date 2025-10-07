import os
import sys

def update_api_key():
    """
    Update the OpenAI API key in the environment variables file
    """
    # Your new valid API key
    new_api_key = input("Enter a valid OpenAI API key: ")
    if not new_api_key:
        print("No API key provided. Exiting.")
        return

    try:
        # Read the entire file
        with open('env.txt', 'r') as file:
            lines = file.readlines()
        
        # Find and replace the OpenAI API key line
        for i, line in enumerate(lines):
            if line.startswith('OPENAI_API_KEY='):
                lines[i] = f'OPENAI_API_KEY={new_api_key}\n'
                print("Found and updated OPENAI_API_KEY in env.txt")
                break
        else:
            # If not found, add it
            lines.append(f'OPENAI_API_KEY={new_api_key}\n')
            print("Added OPENAI_API_KEY to env.txt")
        
        # Write the modified content back to the file
        with open('env.txt', 'w') as file:
            file.writelines(lines)
        
        print("API key updated successfully in env.txt")
        
        # Also update the current environment variable
        os.environ['OPENAI_API_KEY'] = new_api_key
        print("Updated OPENAI_API_KEY in current environment")
        
    except Exception as e:
        print(f"Error updating API key: {str(e)}")

if __name__ == "__main__":
    update_api_key() 