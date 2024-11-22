# AWS Subnet Finder

Script to find next available subnets in AWS VPC with no IP overlap.

## Setup

```bash
# Clone repository
git clone [repository-url]
cd aws-subnet-finder

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure AWS credentials
aws configure
```

## Usage

```bash
python subnet_finder.py <vpc-id> <subnet-prefix> [region]

# Example:
python subnet_finder.py.py vpc-1234567890abcdef0 27
```

### Parameters:
- `vpc-id`: Your AWS VPC ID
- `subnet-prefix`: CIDR prefix (16-28)
- `region`: Optional AWS region

### Output Example:
```
=== VPC Information ===
VPC ID: vpc-1234567890abcdef0
VPC CIDR: 172.31.0.0/16

=== Existing Subnets ===
CIDR: 172.31.0.0/24     (Usable IPs: 254)

=== Next Available /27 Subnets ===
Subnet 1 (AZ: us-east-1a):
CIDR Block: 172.31.1.0/27
...
```
