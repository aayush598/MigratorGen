"""
Example user code using mylib v1.0.0
This file will be migrated to v3.0.0
"""

from mylib import Client
from mylib.helpers import Formatter

# Create a client (old API)
client = Client()

# Old connection style
conn = connect(host="localhost", port=5432)

# Old request method  
response = send_request(conn, "/api/data", verbose=True)

# Old attribute access
print(client.url)

# Deprecated function
data = fetch_data()

# Old method call style
name = client.get_name()

# Formatter from old location
fmt = Formatter()
output = fmt.format(data)