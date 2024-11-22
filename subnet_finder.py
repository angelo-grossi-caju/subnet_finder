#!/usr/bin/env python3
import boto3
import sys
import ipaddress
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class SubnetInfo:
    cidr_block: str
    network_address: str
    broadcast_address: str
    first_usable: str
    last_usable: str
    usable_ips: int
    suggested_az: str

class IncrementalSubnetFinder:
    def __init__(self, vpc_id: str, region: str = None):
        self.vpc_id = vpc_id
        self.ec2 = boto3.client('ec2', region_name=region)
        self.vpc_cidr = self._get_vpc_cidr()
        self.existing_subnets = self._get_existing_subnets()
        self.available_azs = self._get_availability_zones()

    def _get_vpc_cidr(self) -> str:
        try:
            vpc_response = self.ec2.describe_vpcs(VpcIds=[self.vpc_id])
            return vpc_response['Vpcs'][0]['CidrBlock']
        except self.ec2.exceptions.ClientError as e:
            if 'InvalidVpcID.NotFound' in str(e):
                raise ValueError(f"VPC {self.vpc_id} not found!")
            raise

    def _get_existing_subnets(self) -> List[str]:
        try:
            subnets_response = self.ec2.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [self.vpc_id]}]
            )
            return sorted([subnet['CidrBlock'] for subnet in subnets_response['Subnets']])
        except self.ec2.exceptions.ClientError as e:
            print(f"Error getting subnets: {e}")
            return []

    def _get_availability_zones(self) -> List[str]:
        try:
            azs = self.ec2.describe_availability_zones()
            return [az['ZoneName'] for az in azs['AvailabilityZones']]
        except self.ec2.exceptions.ClientError as e:
            print(f"Error getting AZs: {e}")
            return []

    def _find_last_ip(self) -> Optional[ipaddress.IPv4Address]:
        if not self.existing_subnets:
            return None
        
        last_subnet = ipaddress.ip_network(self.existing_subnets[-1])
        return last_subnet.broadcast_address

    def find_next_subnets(self, new_prefix: int, count: int = 3) -> List[SubnetInfo]:
        vpc_net = ipaddress.ip_network(self.vpc_cidr)
        last_ip = self._find_last_ip()
        
        if last_ip is None:
            # If no existing subnets, start from the beginning of VPC CIDR
            start_ip = vpc_net.network_address
        else:
            # Start from the next IP after the last subnet's broadcast address
            start_ip = last_ip + 1

        available_subnets = []
        current_ip = start_ip

        while len(available_subnets) < count:
            # Calculate the next subnet of desired size
            try:
                next_net = ipaddress.ip_network(f"{current_ip}/{new_prefix}", strict=False)
                
                # Verify this subnet is within VPC CIDR
                if next_net.subnet_of(vpc_net):
                    subnet_info = SubnetInfo(
                        cidr_block=str(next_net),
                        network_address=str(next_net.network_address),
                        broadcast_address=str(next_net.broadcast_address),
                        first_usable=str(next_net.network_address + 1),
                        last_usable=str(next_net.broadcast_address - 1),
                        usable_ips=next_net.num_addresses - 2,
                        suggested_az=self.available_azs[len(available_subnets) % len(self.available_azs)]
                    )
                    available_subnets.append(subnet_info)
                    current_ip = next_net.broadcast_address + 1
                else:
                    raise ValueError(f"No more space in VPC CIDR {self.vpc_cidr} for /{new_prefix} subnets")
            except ValueError as e:
                raise ValueError(f"Error calculating next subnet: {str(e)}")

        return available_subnets

    def print_subnet_info(self, new_prefix: int):
        try:
            print("\n=== VPC Information ===")
            print(f"VPC ID: {self.vpc_id}")
            print(f"VPC CIDR: {self.vpc_cidr}")
            
            print("\n=== Existing Subnets ===")
            if self.existing_subnets:
                for subnet in self.existing_subnets:
                    network = ipaddress.ip_network(subnet)
                    print(f"CIDR: {subnet:<18} (Usable IPs: {network.num_addresses - 2})")
            else:
                print("No existing subnets found")
            
            print(f"\n=== Next Available /{new_prefix} Subnets ===")
            next_subnets = self.find_next_subnets(new_prefix)
            
            for i, subnet in enumerate(next_subnets, 1):
                print(f"\nSubnet {i} (AZ: {subnet.suggested_az}):")
                print(f"CIDR Block: {subnet.cidr_block}")
                print(f"Network Address: {subnet.network_address}")
                print(f"Broadcast Address: {subnet.broadcast_address}")
                print(f"Usable IP Range: {subnet.first_usable} - {subnet.last_usable}")
                print(f"Number of usable IPs: {subnet.usable_ips}")

        except ValueError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

def main():
    if len(sys.argv) not in [3, 4]:
        print("Usage: ./subnet_finder.py <vpc-id> <subnet-prefix> [region]")
        print("Example: ./subnet_finders.py vpc-1234567890abcdef0 27 us-east-1")
        sys.exit(1)
    
    vpc_id = sys.argv[1]
    try:
        subnet_prefix = int(sys.argv[2])
        if subnet_prefix not in range(16, 29):
            raise ValueError("Subnet prefix must be between /16 and /28")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    region = sys.argv[3] if len(sys.argv) == 4 else None
    finder = IncrementalSubnetFinder(vpc_id, region)
    finder.print_subnet_info(subnet_prefix)

if __name__ == "__main__":
    main()