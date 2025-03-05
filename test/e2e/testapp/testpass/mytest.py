
def prep(args):
    args.insert(0, "python3")
    args.insert(1, '-m')
    args.insert(2, "test.e2e.testapp")
    return args

run_ok_one = prep(["ok_function"])

out_ok_one = "Doing great"

run_ok_two = ["echo", "-n", "great"]

out_ok_two = "great"

