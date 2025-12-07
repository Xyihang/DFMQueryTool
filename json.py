import json
import logging

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    # 读取并解析JSON文件
    with open('return.txt', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取物品ID和名称的映射关系
    item_mapping = {}
    for item in data['data']['keywords']:
        object_id = item['objectID']
        object_name = item['objectName']
        item_mapping[object_id] = object_name
    
    # 记录结果
    logger.info("物品ID与名称对应关系:")
    for obj_id, name in item_mapping.items():
        logger.info(f"ID: {obj_id} -> 名称: {name}")
    
    # 将结果保存到JSON文件
    with open('item_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(item_mapping, f, ensure_ascii=False, indent=2)
    
    logger.info("结果已保存到 item_mapping.json 文件")
    
except FileNotFoundError:
    logger.error("未找到return.txt文件")
except json.JSONDecodeError as e:
    logger.error(f"JSON解析错误: {e}")
except Exception as e:
    logger.error(f"处理过程中发生错误: {e}")