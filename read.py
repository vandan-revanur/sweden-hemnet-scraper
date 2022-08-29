import json
import pandas as pd

# with open('data.json') as json_file:
#     data = json.load(json_file)
#     print(data)



df_housing = pd.read_csv('hemnet_housing.csv')

print(f'total number of housings in database: {len(df_housing)}')