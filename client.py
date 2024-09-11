#!/usr/bin/env python3

import requests
import sys
import base64

base_url = "http://localhost:8009"

def send_request(endpoint, method='GET', data=None):
    url = f"{base_url}/{endpoint}"
    if method == 'GET':
        response = requests.get(url)
    else:
        response = requests.post(url, json=data)
    return response.json()

def screenshot():
    response = requests.get(f"{base_url}/screenshot")
    if response.status_code == 200:
        screenshot = response.json()['screenshot']
        with open('screenshot.png', 'wb') as f:
            f.write(base64.b64decode(screenshot))
        return "Screenshot saved to screenshot.png"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client.py <command> [args...]")
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]
    
    # commands:
    # open http://example.com
    # click h1
    # type input[type="text"] "Hello, World!"
    # screenshot
    # close
    # scroll up 500
    # scroll down 500
    # scroll left 500
    # scroll right 500
    # get_text h1
    # get_attribute a href
    # execute_script "alert('Hello, World!')"
    # navigate back
    # navigate forward
    # reload
    # list_elements a
    
    if command == 'open':
        url = args[0]
        response = send_request('open', 'POST', {'url': url})
        print(response['message'])
    elif command == 'close':
        response = send_request('close', 'POST')
        print(response['message'])
    elif command == 'screenshot':
        print(screenshot())
    elif command == 'click':
        selector = args[0]
        response = send_request('click', 'POST', {'selector': selector})
        print(response['message'])
    elif command == 'click2':
        selector = args[0]
        response = send_request('click2', 'POST', {'selector': selector})
        print(response['message'])
    elif command == 'type':
        selector = args[0]
        text = args[1]
        response = send_request('type', 'POST', {'selector': selector, 'text': text})
        print(response['message'])
    elif command == 'scroll':
        direction = args[0]
        amount = args[1]
        response = send_request('scroll', 'POST', {'direction': direction, 'amount': amount})
        print(response['message'])
    elif command == 'get_text':
        selector = args[0]
        response = send_request('get_text', 'POST', {'selector': selector})
        print(response['message'])
    elif command == 'get_attribute':
        selector = args[0]
        attribute = args[1]
        response = send_request('get_attribute', 'POST', {'selector': selector, 'attribute': attribute})
        print(response['message'])
    elif command == 'execute_script':
        script = args[0]
        response = send_request('execute_script', 'POST', {'script': script})
        print(response['message'])
    elif command == 'navigate':
        action = args[0]
        response = send_request(action, 'POST')
        print(response['message'])
    elif command == 'reload':
        response = send_request('reload', 'POST')
        print(response['message'])
    elif command == 'list_elements':
        selector = args[0]
        response = send_request('list_elements', 'POST', {'selector': selector})
        elements = response['elements']
        print(f'Found {len(elements)} elements')
        for element in elements:
            print(element)
    else:
        print("Invalid command")
        sys.exit(1)
