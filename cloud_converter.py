import json
import sys




VOLUME_TYPE_MAPPING = {
    "gp2": "pd-standard",
    "gp3": "pd-balanced",
    "io1": "pd-ssd",
    "io2": "pd-ssd",
    "sc1": "pd-standard",
    "st1": "pd-standard"
}




INSTANCE_TYPE_MAPPING = {
   
    "t3.micro": "e2-micro",
    "t3.small": "e2-small",
    "t3.medium": "e2-medium",
    "t3.large": "e2-standard-2",
    "m5.large": "n2-standard-2",
    "m5.xlarge": "n2-standard-4",
    "m5.2xlarge": "n2-standard-8",
    "m5.4xlarge": "n2-standard-16",


   
    "c5.large": "c2-standard-2",
    "c5.xlarge": "c2-standard-4",
    "c5.2xlarge": "c2-standard-8",
    "c5.4xlarge": "c2-standard-16",
    "c5.9xlarge": "c2-standard-30",
    "c5.18xlarge": "c2-standard-60",


   
    "r5.large": "n2-highmem-2",
    "r5.xlarge": "n2-highmem-4",
    "r5.2xlarge": "n2-highmem-8",
    "r5.4xlarge": "n2-highmem-16",
    "r5.12xlarge": "n2-highmem-48",
    "r5.24xlarge": "n2-highmem-80",


   
    "x1e.8xlarge": "m2-ultramem-208",
    "x1e.xlarge": "m2-megamem-96",
    "z1d.large": "c2d-standard-2",


 


   
    "i3.large": "n2-standard-2",
    "d2.xlarge": "n2-standard-4",
    "h1.2xlarge": "n2-standard-8",
}






def convert_aws_to_gcp(aws_json):
    aws_instance_block = aws_json["resource"]["aws_instance"]
    aws_name = list(aws_instance_block.keys())[0]
    aws_instance = aws_instance_block[aws_name]


    aws_type = aws_instance.get("instance_type", "t2.micro")
    gcp_type = INSTANCE_TYPE_MAPPING.get(aws_type, "e2-micro")


    block_device = aws_instance.get("root_block_device", {})
    volume_size = block_device.get("volume_size", 10)
    aws_volume_type = block_device.get("volume_type", "gp2")
    gcp_disk_type = VOLUME_TYPE_MAPPING.get(aws_volume_type, "pd-standard")


    gcp_labels = aws_instance.get("tags", {})
    subnet_id = aws_instance.get("subnet_id", "default")
    public_ip = aws_instance.get("associate_public_ip_address", True)


    gcp_config = {
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
                    "labels": gcp_labels,
                    "network_interface": [
                        {
                            "network": subnet_id,
                            "access_config": [{}] if public_ip else []
                        }
                    ]
                }
            }
        }
    }


    return gcp_config




def convert_gcp_to_aws(gcp_json):
    gcp_instance_block = gcp_json["resource"]["google_compute_instance"]
    gcp_name = list(gcp_instance_block.keys())[0]
    gcp_instance = gcp_instance_block[gcp_name]


    gcp_type = gcp_instance.get("machine_type", "e2-micro")
    aws_type = {v: k for k, v in INSTANCE_TYPE_MAPPING.items()}.get(gcp_type, "t2.micro")


    disk_params = gcp_instance.get("boot_disk", {}).get("initialize_params", {})
    volume_size = disk_params.get("size", 10)
    gcp_disk_type = disk_params.get("type", "pd-standard")
    aws_volume_type = {v: k for k, v in VOLUME_TYPE_MAPPING.items()}.get(gcp_disk_type, "gp2")


    gcp_labels = gcp_instance.get("labels", {})
    gcp_network = gcp_instance.get("network_interface", [{}])[0]
    subnet_id = gcp_network.get("network", "default")
    public_ip = bool(gcp_network.get("access_config", [{}]))


    aws_config = {
        "resource": {
            "aws_instance": {
                gcp_name: {
                    "ami": "ami-12345678",
                    "instance_type": aws_type,
                    "associate_public_ip_address": public_ip,
                    "subnet_id": subnet_id,
                    "tags": gcp_labels,
                    "root_block_device": {
                        "volume_size": volume_size,
                        "volume_type": aws_volume_type
                    }
                }
            }
        }
    }


    return aws_config




def main():
    if len(sys.argv) != 3:
        print("Usage: python cloud_converter.py <input_file.json> <conversion_direction>")
        print("conversion_direction: aws_to_gcp or gcp_to_aws")
        sys.exit(1)


    input_file = sys.argv[1]
    direction = sys.argv[2]


    with open(input_file, "r") as f:
        data = json.load(f)


    if direction == "aws_to_gcp":
        output = convert_aws_to_gcp(data)
        output_file = "gcp_output.tf.json"
    elif direction == "gcp_to_aws":
        output = convert_gcp_to_aws(data)
        output_file = "aws_output.tf.json"
    else:
        print("Invalid conversion direction. Use 'aws_to_gcp' or 'gcp_to_aws'")
        sys.exit(1)


    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)


    print(f" Conversion complete. Output written to `{output_file}`")




if __name__ == "__main__":
    main()





