import json
import sys
import os




aws_to_gcp_instance = {
    "t2.micro": "e2-micro",
    "t3.micro": "e2-micro",
    "t3.small": "e2-small",
    "t3.medium": "e2-medium",
    "m5.large": "n2-standard-2"
}
gcp_to_aws_instance = {v: k for k, v in aws_to_gcp_instance.items()}


aws_to_gcp_disk = {
    "gp2": "pd-balanced",
    "gp3": "pd-balanced",
    "io1": "pd-ssd",
    "io2": "pd-ssd",
    "st1": "pd-standard",
    "sc1": "pd-standard"
}
gcp_to_aws_disk = {v: k for k, v in aws_to_gcp_disk.items()}


def convert_aws_to_gcp(aws_json):
    aws_instance_block = aws_json["resource"]["aws_instance"]
    aws_name = list(aws_instance_block.keys())[0]
    aws_instance = aws_instance_block[aws_name]


    aws_type = aws_instance.get("instance_type", "t3.micro")
    gcp_type = aws_to_gcp_instance.get(aws_type, "e2-micro")


    aws_disk = aws_instance.get("root_block_device", {})
    volume_size = aws_disk.get("volume_size", 10)
    volume_type = aws_disk.get("volume_type", "gp2")
    gcp_disk_type = aws_to_gcp_disk.get(volume_type, "pd-balanced")


    return {
        "provider": {
            "google": {
                "project": "your-gcp-project-id",
                "region": "us-central1",
                "zone": "us-central1-a"
            }
        },
        "resource": {
            "google_compute_instance": {
                aws_name: {
                    "name": aws_name.replace("_", "-"),
                    "machine_type": gcp_type,
                    "zone": "us-central1-a",
                    "boot_disk": {
                        "initialize_params": {
                            "image": "debian-cloud/debian-11",
                            "size": volume_size,
                            "type": gcp_disk_type
                        }
                    },
                    "network_interface": [
                        {
                            "network": "default",
                            "access_config": [{}]
                        }
                    ]
                }
            }
}
    }


def convert_gcp_to_aws(gcp_json):
    gcp_instance_block = gcp_json["resource"]["google_compute_instance"]
    gcp_name = list(gcp_instance_block.keys())[0]
    gcp_instance = gcp_instance_block[gcp_name]


    gcp_type = gcp_instance.get("machine_type", "e2-micro")
    aws_type = gcp_to_aws_instance.get(gcp_type, "t3.micro")


    disk = gcp_instance.get("boot_disk", {}).get("initialize_params", {})
    volume_size = disk.get("size", 10)
    disk_type = disk.get("type", "pd-balanced")
    aws_volume_type = gcp_to_aws_disk.get(disk_type, "gp2")


    return {
        "provider": {
            "aws": {
                "region": "us-east-1"
            }
        },
        "resource": {
            "aws_instance": {
                gcp_name: {
                    "ami": "ami-12345678",
                    "instance_type": aws_type,
                    "associate_public_ip_address": True,
                    "root_block_device": {
                        "volume_size": volume_size,
                        "volume_type": aws_volume_type
                    }
                }
            }
        }
    }


def detect_and_convert(json_data):
    if "aws_instance" in json_data.get("resource", {}):
        return convert_aws_to_gcp(json_data), "gcp_main.tf.json"
    elif "google_compute_instance" in json_data.get("resource", {}):
        return convert_gcp_to_aws(json_data), "aws_main.tf.json"
    else:
        print(" Unsupported or unrecognized configuration.")
        sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print("Usage: python cloud_tf_converter.py <input.json>")
        sys.exit(1)


    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f" File not found: {input_file}")
        sys.exit(1)


    with open(input_file, "r") as f:
        json_data = json.load(f)


    output_data, output_filename = detect_and_convert(json_data)


    with open(output_filename, "w") as f:
        json.dump(output_data, f, indent=2)


    print(f" Converted configuration saved to {output_filename}")


if __name__ == "__main__":
    main()
