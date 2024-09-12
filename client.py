#!/usr/bin/env python3
import requests
import base64
from pathlib import Path
# Need to rename the click package so it doesn't clash with 
# our click command
import click as cl

base_url = "http://localhost:8009"

def send_request(endpoint, method='GET', data=None):
    url = f"{base_url}/{endpoint}"
    if method == 'GET':
        response = requests.get(url)
    else:
        response = requests.post(url, json=data)
    return response.json()

@cl.group()
def cli():
    pass

@cli.command()
@cl.argument('url')
def open(url):
    response = send_request('open', 'POST', {'url': url})
    print(response['message'])

@cli.command()
def close():
    response = send_request('close', 'POST')
    print(response['message'])

@cli.command()
def screenshot():
    response = requests.get(f"{base_url}/screenshot")
    if response.status_code == 200:
        screenshot_data = response.json()['screenshot']
        path = Path('screenshot.png')
        path.write_bytes(base64.b64decode(screenshot_data))
        print("Screenshot saved to screenshot.png")

@cli.command()
@cl.argument('selector')
def click(selector):
    response = send_request('click', 'POST', {'selector': selector})
    print(response['message'])

@cli.command()
@cl.argument('selector')
@cl.argument('text')
def type(selector, text):
    response = send_request('type', 'POST', {'selector': selector, 'text': text})
    print(response['message'])

@cli.command()
@cl.argument('direction')
@cl.argument('amount', type=int)
def scroll(direction, amount):
    response = send_request('scroll', 'POST', {'direction': direction, 'amount': amount})
    print(response['message'])

@cli.command()
@cl.argument('selector')
def get_text(selector):
    response = send_request('get_text', 'POST', {'selector': selector})
    print(response['message'])

@cli.command()
@cl.argument('selector')
@cl.argument('attribute')
def get_attribute(selector, attribute):
    response = send_request('get_attribute', 'POST', {'selector': selector, 'attribute': attribute})
    print(response['message'])

@cli.command()
@cl.argument('script')
def execute_script(script):
    response = send_request('execute_script', 'POST', {'script': script})
    print(response['message'])

@cli.command()
@cl.argument('action')
def navigate(action):
    response = send_request(action, 'POST')
    print(response['message'])

@cli.command()
def reload():
    response = send_request('reload', 'POST')
    print(response['message'])

@cli.command()
@cl.argument('selector')
def list_elements(selector):
    response = send_request('list_elements', 'POST', {'selector': selector})
    elements = response['elements']
    print(f'Found {len(elements)} elements')
    for element in elements:
        print(element)

if __name__ == "__main__":
    cli()