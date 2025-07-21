# agent.py
import requests
import json
import os

def process_job_data(json_directory, start_from=0, process_count=None):
    """Process all JSON files in the directory using a local Ollama LLM
    
    Args:
        json_directory: Directory containing JSON files
        start_from: Index to start processing from (skip earlier files)
        process_count: Maximum number of files to process (None for all)
    """
    # Get all JSON files in the directory
    if not os.path.exists(json_directory):
        print(f"Directory {json_directory} does not exist.")
        return
    
    json_files = [f for f in os.listdir(json_directory) if f.endswith('.json')]
    if not json_files:
        print(f"No JSON files found in {json_directory}")
        return
    
    total_files = len(json_files)
    print(f"Found {total_files} JSON files to process")
    
    # Apply start_from and process_count limits
    if start_from > 0:
        print(f"Starting from file #{start_from+1}")
        json_files = json_files[start_from:]
    
    if process_count is not None:
        print(f"Processing up to {process_count} files")
        json_files = json_files[:process_count]
    
    # Create a directory for processed data if it doesn't exist
    processed_dir = os.path.join(json_directory, "processed")
    os.makedirs(processed_dir, exist_ok=True)
    
    for file in json_files:
        file_path = os.path.join(json_directory, file)
        print(f"Processing {file}...")
        
        try:
            with open(file_path, 'r') as f:
                job_data = json.load(f)
            
            # Process each key in the JSON data without job_url key 
            for key in job_data:
                if key != "job_description":
                    continue
                prompt = f"""
                You are a job data analyst. I will provide you with raw job data scraped from LinkedIn.
                As key value pairs, organize the values in a way that is easy to read and understand.
                
                Here is the job data:
                {json.dumps(job_data[key], indent=2)}
                key: {key}
                """
                
                try:
                    print(f"Sending request to Ollama for key '{key}' with prompt: {prompt} (this may take a few minutes)...")
                    response = requests.post('http://localhost:11434/api/generate', 
                                            json={
                                                'model': 'llama2',
                                                'prompt': prompt,
                                                'stream': False,
                                                'temperature': 0.1
                                            },
                                            timeout=300)
                    
                    # Extract and save processed data
                    result = response.json()
                    processed_data = result['response']
                    print(f"Response received from Ollama for key '{key}" + "response: " + processed_data)
                    
                    # Try to extract JSON if it's embedded in markdown or other text
                    json_str = processed_data
                    if "```json" in processed_data:
                        json_start = processed_data.find("```json")
                        json_end = processed_data.find("```", json_start + 7)
                        json_str = processed_data[json_start + 7:json_end].strip()
                    elif "```" in processed_data:
                        json_start = processed_data.find("```")
                        json_end = processed_data.find("```", json_start + 3)
                        json_str = processed_data[json_start + 3:json_end].strip()
                    
                    try:
                        # Parse JSON
                        processed_json = json.loads(json_str)
                        
                        # Save as formatted JSON
                        output_filename = f"processed_{key}_{file}"
                        output_path = os.path.join(processed_dir, output_filename)
                        with open(output_path, 'w') as f:
                            json.dump(processed_json, f, indent=4)
                        print(f"✓ Successfully processed key '{key}' and saved to {output_filename}")
                    
                    except json.JSONDecodeError:
                        # If we can't parse as JSON, save the raw response
                        output_filename = f"raw_{key}_{file.replace('.json', '.txt')}"
                        output_path = os.path.join(processed_dir, output_filename)
                        with open(output_path, 'w') as f:
                            f.write(processed_data)
                        print(f"! Couldn't parse as JSON for key '{key}'. Raw response saved to {output_filename}")
                
                except requests.exceptions.Timeout:
                    print(f"Request timed out for key '{key}'. The data may be too large for Ollama to process quickly.")
                    output_filename = f"timeout_{key}_{file.replace('.json', '.txt')}"
                    output_path = os.path.join(processed_dir, output_filename)
                    with open(output_path, 'w') as f:
                        f.write(f"Processing timed out for key '{key}'")
                
                except requests.exceptions.ConnectionError:
                    print(f"Connection error: Cannot connect to Ollama at http://localhost:11434")
                    print("Make sure Ollama is running and accessible.")
                    print("Try these steps:\n1. Restart Ollama\n2. Run 'ollama serve' in a terminal\n3. Check if you can access http://localhost:11434 in a browser")
                    return  # Exit the entire function if we can't connect
                
                except requests.exceptions.RequestException as e:
                    print(f"Error calling Ollama API for key '{key}': {e}")
                    continue  # Skip this key but try the next
                
        except Exception as e:
            print(f"Error processing file {file}: {e}")
            continue  # Skip this file but try the next

def main():
    # Directory containing your scraped job JSON files
    job_search_dir = input("Enter the job search directory name (e.g. 'Junior Devops Engineer'): ")
    
    # Check if Ollama is running
    try:
        print("Checking if Ollama is running...")
        health_response = requests.get('http://localhost:11434/api/health', timeout=5)
        if health_response.status_code == 200:
            print("✓ Ollama is running")
        else:
            print("! Ollama seems to be running but returned an unexpected status code")
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to Ollama. Please make sure it's running.")
        print("  Try running 'ollama serve' in a terminal or restart the Ollama application.")
        return
    except Exception as e:
        print(f"! Error checking Ollama status: {e}")
    
    # Check if we need to download the model first
    try:
        print("Checking if model 'llama2' is available...")
        models_response = requests.get('http://localhost:11434/api/tags', timeout=5)
        models = models_response.json().get('models', [])
        model_exists = any(model['name'] == 'llama2' for model in models)
        
        if not model_exists:
            print("Model 'llama2' not found. Pulling it now (this might take a while)...")
            pull_response = requests.post('http://localhost:11434/api/pull', 
                                        json={'name': 'llama2'})
            print("Model downloaded successfully.")
        else:
            print("✓ Model 'llama2' is already downloaded and ready to use")
    except Exception as e:
        print(f"Could not check for models: {e}")
        print("You might need to run 'ollama pull llama2' in a terminal.")
        return
    
    # Ask for processing options
    try:
        start_from = int(input("Start processing from file # (0 to start from beginning): "))
    except ValueError:
        start_from = 0
    
    try:
        process_count_input = input("Number of files to process (press Enter to process all): ")
        process_count = int(process_count_input) if process_count_input.strip() else None
    except ValueError:
        process_count = None
        
    # Process the job data
    process_job_data(job_search_dir, start_from, process_count)

if __name__ == "__main__":
    main()
