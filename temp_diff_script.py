import yaml


def load_specs(file):
    with open(file, "r") as file:
        return yaml.safe_load(file)


def calculate_diff(spec1, spec2):
    diff = {}
    for endpoint in spec1:
        if endpoint not in spec2 or spec1[endpoint] != spec2[endpoint]:
            diff[endpoint] = {"diff": spec1[endpoint], "new": spec2.get(endpoint)}
    return diff


cribl_stream_4_13 = load_specs("cribl_api_specs/cribl-stream-4.13.yml")
cribl_stream_4_14 = load_specs("cribl_api_specs/cribl-stream-4.14.yml")
cribl_stream_4_15 = load_specs("cribl_api_specs/cribl-stream-4.15.yml")

diff_btw_v413_v414 = calculate_diff(cribl_stream_4_13, cribl_stream_4_14)
diff_btw_v414_v415 = calculate_diff(cribl_stream_4_14, cribl_stream_4_15)

print("Diff between versions 4.1.3 and 4.1.4:")
for endpoint in diff_btw_v413_v414:
    print(f"{endpoint}: {diff_btw_v413_v414[endpoint]['new']}")

print("\n\nDiff between versions 4.1.4 and 4.1.5:")
for endpoint in diff_btw_v414_v415:
    print(f"{endpoint}: {diff_btw_v414_v415[endpoint]['new']}")
