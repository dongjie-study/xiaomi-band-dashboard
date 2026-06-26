"""
Update 618复盘报告.html with new data from 618_report_data.json
"""
import json
import re

# Read the JSON data
with open(r'C:\Users\Administrator\Desktop\小米手环直播间销量分析\618_report_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Read the HTML template
with open(r'C:\Users\Administrator\Desktop\小米手环直播间销量分析\618复盘报告.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the data in the HTML
# Find the D = {...} pattern and replace it
json_str = json.dumps(data, ensure_ascii=False)
new_html = re.sub(r'const D = \{[^;]+\};', f'const D = {json_str};', html)

# Write the updated HTML
with open(r'C:\Users\Administrator\Desktop\小米手环直播间销量分析\618复盘报告.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Updated 618复盘报告.html with new data")
print(f"Total categories: {len(data['cat_all'])}")
print("\n小米手环产品:")
for item in data['cat_all']:
    if '手环' in item['品类']:
        print(f"  {item['品类']}: {item['订单数']}单, {item['GSV']:,.0f}元 ({item['占比']}%)")
