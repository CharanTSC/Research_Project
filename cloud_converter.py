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
    "t2.micro": "e2-micro",
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
    "z1d.large": "c2d-standard-2"
}


def convert_aws_to_gcp(aws_json):
    gcp_config = {"resource": {}}


   
    for name, vpc in aws_json.get("resource", {}).get("aws_vpc", {}).items():
        gcp_config["resource"].setdefault("google_compute_network", {})[name] = {
            "name": vpc.get("tags", {}).get("Name", name),
            "auto_create_subnetworks": vpc.get("enable_dns_support", True)
        }


   
    for name, subnet in aws_json.get("resource", {}).get("aws_subnet", {}).items():
        gcp_config["resource"].setdefault("google_compute_subnetwork", {})[name] = {
            "name": subnet.get("tags", {}).get("Name", name),
            "ip_cidr_range": subnet.get("cidr_block"),
            "region": "us-central1",
            "network": subnet.get("vpc_id", "default")
        }


   
    for name, sg in aws_json.get("resource", {}).get("aws_security_group", {}).items():
        ingress_rules = []
        for rule in sg.get("ingress", []):
            ingress_rules.append({
                "protocol": rule.get("protocol", "tcp"),
                "ports": [str(rule.get("from_port"))] if rule.get("from_port") is not None else [],
                "source_ranges": rule.get("cidr_blocks", ["0.0.0.0/0"])
            })
        gcp_config["resource"].setdefault("google_compute_firewall", {})[name] = {
            "name": sg.get("tags", {}).get("Name", name),
            "network": sg.get("vpc_id", "default"),
            "direction": "INGRESS",
            "allow": ingress_rules
        }


   
    for name, route in aws_json.get("resource", {}).get("aws_route", {}).items():
        gcp_config["resource"].setdefault("google_compute_route", {})[name] = {
            "name": name,
            "network": route.get("vpc_id", "default"),
            "dest_range": route.get("destination_cidr_block", "0.0.0.0/0"),
            "next_hop_gateway": "default-internet-gateway"
        }


   
    for name, instance in aws_json.get("resource", {}).get("aws_instance", {}).items():
        aws_type = instance.get("instance_type", "t2.micro")
        gcp_type = INSTANCE_TYPE_MAPPING.get(aws_type, "e2-micro")


        block_device = instance.get("root_block_device", {})
        volume_size = block_device.get("volume_size", 10)
        aws_volume_type = block_device.get("volume_type", "gp2")
        gcp_disk_type = VOLUME_TYPE_MAPPING.get(aws_volume_type, "pd-standard")


        gcp_labels = instance.get("tags", {})
        subnet_id = instance.get("subnet_id", "default")
        public_ip = instance.get("associate_public_ip_address", True)


        gcp_config["resource"].setdefault("google_compute_instance", {})[name] = {
            "name": name.replace("_", "-"),
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
                    "subnetwork": subnet_id,
                    "access_config": [{}] if public_ip else []
                }
            ]
        }


    return gcp_config




def convert_gcp_to_aws(gcp_json):
    aws_config = {"resource": {}}


   
    for name, vpc in gcp_json.get("resource", {}).get("google_compute_network", {}).items():
        aws_config["resource"].setdefault("aws_vpc", {})[name] = {
            "cidr_block": "10.0.0.0/16",
            "enable_dns_support": vpc.get("auto_create_subnetworks", True),
            "tags": {"Name": vpc.get("name", name)}
        }


   
    for name, subnet in gcp_json.get("resource", {}).get("google_compute_subnetwork", {}).items():
        aws_config["resource"].setdefault("aws_subnet", {})[name] = {
            "vpc_id": subnet.get("network", "default"),
            "cidr_block": subnet.get("ip_cidr_range"),
            "tags": {"Name": subnet.get("name", name)}
        }


   
    for name, firewall in gcp_json.get("resource", {}).get("google_compute_firewall", {}).items():
        ingress_rules = []
        for allow in firewall.get("allow", []):
            ingress_rules.append({
                "protocol": allow.get("protocol", "tcp"),
                "from_port": int(allow.get("ports", ["0"])[0]),
                "to_port": int(allow.get("ports", ["0"])[0]),
                "cidr_blocks": allow.get("source_ranges", ["0.0.0.0/0"])
            })
        aws_config["resource"].setdefault("aws_security_group", {})[name] = {
            "vpc_id": firewall.get("network", "default"),
            "ingress": ingress_rules,
            "tags": {"Name": firewall.get("name", name)}
        }


   
    for name, route in gcp_json.get("resource", {}).get("google_compute_route", {}).items():
        aws_config["resource"].setdefault("aws_route", {})[name] = {
            "vpc_id": route.get("network", "default"),
            "destination_cidr_block": route.get("dest_range", "0.0.0.0/0"),
            "gateway_id": "igw-12345678"
        }


   
    for name, instance in gcp_json.get("resource", {}).get("google_compute_instance", {}).items():
        gcp_type = instance.get("machine_type", "e2-micro")
        aws_type = {v: k for k, v in INSTANCE_TYPE_MAPPING.items()}.get(gcp_type, "t2.micro")


        disk_params = instance.get("boot_disk", {}).get("initialize_params", {})
        volume_size = disk_params.get("size", 10)
        gcp_disk_type = disk_params.get("type", "pd-standard")
        aws_volume_type = {v: k for k, v in VOLUME_TYPE_MAPPING.items()}.get(gcp_disk_type, "gp2")


        gcp_labels = instance.get("labels", {})
        subnet_id = instance.get("network_interface", [{}])[0].get("subnetwork", "default")
        public_ip = bool(instance.get("network_interface", [{}])[0].get("access_config", [{}]))


        aws_config["resource"].setdefault("aws_instance", {})[name] = {
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


    return aws_config




def main():
    if len(sys.argv) != 3:
        print("Usage: python aws_to_gcp_converter.py <input_file.json> <conversion_direction>")
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


    print(f"✅ Conversion complete. Output written to `{output_file}`")




if __name__ == "__main__":
    main()




