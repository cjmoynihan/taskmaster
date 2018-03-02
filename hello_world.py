__author__ = 'cj'

import toga

def button_handler(widget):
    # Can this function name be anything?
    # Probably called 'widget' by convention
    print("hello")

def build(app):
    box = toga.Box()

    button = toga.Button('Hello world', on_press=button_handler)
    button.style.padding = 50
    button.style.flex = 1
    box.add(button)

    return box

def main():
    return toga.App('First App', 'org.pybee.helloworld', startup=build)

if __name__ == '__main__':
    main().main_loop()