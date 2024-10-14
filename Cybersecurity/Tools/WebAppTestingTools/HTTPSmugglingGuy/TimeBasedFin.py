import os
import base64
import xml.etree.ElementTree as ET
import subprocess
import time
import argparse

def load_items_from_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    return root.findall(".//item")

def decode_base64(encoded_text):
    return base64.b64decode(encoded_text).decode('utf-8', errors='ignore')

def modify_request_clte(request):
    lines = request.split('\n')
    modified = []
    content_length_index = None
    for i, line in enumerate(lines):
        if line.startswith('Content-Length:'):
            content_length_index = i
        if line.startswith('Transfer-Encoding:'):
            modified.insert(content_length_index, line)
            continue
        modified.append(line)
    body_start = modified.index('') + 1
    modified.insert(body_start, 'X')
    return '\n'.join(modified)

def modify_request_tecl(request):
    lines = request.split('\n')
    modified = []
    transfer_encoding_index = None
    for i, line in enumerate(lines):
        if line.startswith('Transfer-Encoding:'):
            transfer_encoding_index = i
        if line.startswith('Content-Length:'):
            modified.insert(transfer_encoding_index, line)
            continue
        modified.append(line)
    body_start = modified.index('') + 1
    modified.insert(body_start, 'X')
    return '\n'.join(modified)

def send_curl_request(request, url):
    curl_command = ['curl', '-X', 'POST', url, '-H', request, '-s', '-o', '/dev/null', '-w', '%{time_total}']
    start_time = time.time()
    result = subprocess.run(curl_command, capture_output=True, text=True)
    end_time = time.time()
    return end_time - start_time

def time_based_testing(xml_file, business, asset_type, asset_value, time_threshold=0.1):
    items = load_items_from_xml(xml_file)

    base_output_dir = "/home/kali/Desktop/BugBountyWork/"
    main_dir = os.path.join(base_output_dir, business, asset_type, asset_value,
                            "WEBENVFINAL", "Advanced Topics", "host-header", "Techniques", "TimeBasedTesting")
    os.makedirs(main_dir, exist_ok=True)

    timing_file = os.path.join(main_dir, "timing.txt")

    # Use asset_value as the URL
    url = asset_value

    with open(timing_file, 'w') as timing:
        for i, item in enumerate(items):
            request_element = item.find("request")

            if request_element is not None and request_element.text:
                try:
                    decoded_request = decode_base64(request_element.text)

                    # Test for CL.TE
                    modified_request_clte = modify_request_clte(decoded_request)

                    original_time = send_curl_request(decoded_request, url)
                    modified_time_clte = send_curl_request(modified_request_clte, url)

                    timing.write(f"Item {i + 1}:\n")
                    timing.write(f"Original request time: {original_time}\n")
                    timing.write(f"Modified CL.TE request time: {modified_time_clte}\n")

                    if abs(original_time - modified_time_clte) > time_threshold:
                        timing.write(f"Potential CL.TE vulnerability detected in item {i + 1}\n")

                    # Test for TE.CL
                    modified_request_tecl = modify_request_tecl(decoded_request)
                    modified_time_tecl = send_curl_request(modified_request_tecl, url)

                    timing.write(f"Modified TE.CL request time: {modified_time_tecl}\n")

                    if abs(original_time - modified_time_tecl) > time_threshold:
                        timing.write(f"Potential TE.CL vulnerability detected in item {i + 1}\n")

                    timing.write("\n")

                except Exception as e:
                    print(f"Error processing item {i + 1}: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Time-Based Testing Scanner")
    parser.add_argument("xml_file", help="Input XML file to scan")
    parser.add_argument("--business", required=True, help="Business name")
    parser.add_argument("--asset_type", required=True, help="Asset type")
    parser.add_argument("--asset_value", required=True, help="Asset value (used as the target URL)")

    args = parser.parse_args()

    time_based_testing(args.xml_file, args.business, args.asset_type, args.asset_value)
