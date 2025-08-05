#!/usr/bin/env python3
"""Comprehensive Whisper service diagnostic"""

import requests
import json

def diagnose_whisper(base_url="http://localhost:9000"):
    print(f"=== Whisper Service Diagnostic ===")
    print(f"Base URL: {base_url}\n")
    
    # 1. Check service health
    print("1. Checking service health...")
    try:
        response = requests.get(f"{base_url}/docs")
        print(f"   ✓ Service is accessible (status: {response.status_code})")
    except Exception as e:
        print(f"   ✗ Service not accessible: {e}")
        return
    
    # 2. Get API specification
    print("\n2. Getting API specification...")
    try:
        response = requests.get(f"{base_url}/openapi.json")
        if response.status_code == 200:
            api_spec = response.json()
            print(f"   ✓ API Title: {api_spec.get('info', {}).get('title', 'Unknown')}")
            print(f"   ✓ API Version: {api_spec.get('info', {}).get('version', 'Unknown')}")
            
            # Get ASR endpoint details
            asr_endpoint = api_spec.get('paths', {}).get('/asr', {})
            if asr_endpoint:
                post_spec = asr_endpoint.get('post', {})
                print(f"\n3. ASR Endpoint Details:")
                print(f"   Summary: {post_spec.get('summary', 'N/A')}")
                
                # Check request body spec
                request_body = post_spec.get('requestBody', {})
                content = request_body.get('content', {})
                
                print(f"\n   Expected Content Type(s):")
                for content_type in content.keys():
                    print(f"   - {content_type}")
                
                # Get schema details
                multipart = content.get('multipart/form-data', {})
                schema = multipart.get('schema', {})
                properties = schema.get('properties', {})
                
                print(f"\n   Expected Parameters:")
                for param_name, param_spec in properties.items():
                    param_type = param_spec.get('type', 'unknown')
                    param_format = param_spec.get('format', '')
                    param_enum = param_spec.get('enum', [])
                    param_default = param_spec.get('default', 'no default')
                    
                    print(f"   - {param_name}:")
                    print(f"     Type: {param_type} {param_format}")
                    if param_enum:
                        print(f"     Allowed values: {param_enum}")
                    print(f"     Default: {param_default}")
                
                # Check required fields
                required = schema.get('required', [])
                if required:
                    print(f"\n   Required fields: {required}")
            
        else:
            print(f"   ✗ Could not get API spec: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error getting API spec: {e}")
    
    # 3. Test minimal request
    print("\n\n4. Testing minimal ASR request...")
    print("   Creating tiny test file...")
    
    # Create a minimal WAV file (44 bytes - smallest valid WAV)
    wav_header = bytearray([
        0x52, 0x49, 0x46, 0x46,  # "RIFF"
        0x24, 0x00, 0x00, 0x00,  # File size - 8
        0x57, 0x41, 0x56, 0x45,  # "WAVE"
        0x66, 0x6D, 0x74, 0x20,  # "fmt "
        0x10, 0x00, 0x00, 0x00,  # Subchunk1Size
        0x01, 0x00,              # AudioFormat (PCM)
        0x01, 0x00,              # NumChannels
        0x44, 0xAC, 0x00, 0x00,  # SampleRate (44100)
        0x88, 0x58, 0x01, 0x00,  # ByteRate
        0x02, 0x00,              # BlockAlign
        0x10, 0x00,              # BitsPerSample
        0x64, 0x61, 0x74, 0x61,  # "data"
        0x00, 0x00, 0x00, 0x00   # Subchunk2Size
    ])
    
    try:
        url = f"{base_url}/asr"
        files = {'audio_file': ('test.wav', bytes(wav_header), 'audio/wav')}
        
        # Try with minimal parameters
        print("   Sending minimal request...")
        response = requests.post(url, files=files, timeout=10)
        
        print(f"   Response status: {response.status_code}")
        print(f"   Response headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"   Response body: {response.text}")
            
            # Try to parse error details
            try:
                error_detail = response.json()
                print(f"\n   Error details (parsed):")
                print(json.dumps(error_detail, indent=2))
            except:
                pass
    except Exception as e:
        print(f"   ✗ Request failed: {e}")

if __name__ == "__main__":
    diagnose_whisper()