import sys
from types import FunctionType

def produce_output():
    print("here is some output")

def exit_with_code_one():
    sys.exit(1)

def buggy_function():
    val = "" + []
    return val

def ok_function():
    print("Doing great")

def main():
    args = sys.argv[1:]
    fns = globals()
    for arg in args:
        if arg in fns:
            if isinstance(fns[arg], FunctionType):
                fns[arg]()
            else:
                print(f"{arg} is not a function")
        else:
            print(f"Cannot find function {arg}")

if __name__ == "__main__":
    main()
