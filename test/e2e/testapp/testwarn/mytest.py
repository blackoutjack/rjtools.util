
def prep(args):
    args.insert(0, "python3")
    args.insert(1, '-m')
    args.insert(2, "test.e2e.testapp")
    return args

run_ok_function = prep(["ok_function"])

out_ok_function = "Doing great"


