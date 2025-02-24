
def prep(args):
    args.insert(0, "python3")
    args.insert(1, '-m')
    args.insert(2, "test.testapp")
    return args

run_ok_function = prep(["ok_function"])

out_ok_function = "Doing great"

run_buggy_function = prep(["buggy_function"])

out_buggy_function = "Meant to fail"

