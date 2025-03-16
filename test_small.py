from src import component_extractor

def greet(name):
    return 'hello '+ name

class Greeter:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return 'hello ' + self.name

    def sayonara(self):
        return 'Sayonara ' + self.name

def add_mul(x, y, z):
    def add(x, y):
        return x + y
    def mul(x, y):
        return x * y
    return mul(x, add(y, z))

NAME = 'Rohan'
print(greet(NAME))

g = Greeter(NAME)
print(g.sayonara())

print(add_mul(
    1, 2, 3
))


s = '''this is
a multi line
statement
'''.strip()
