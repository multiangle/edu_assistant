import os
import base64
from openai import OpenAI

api_key = "API_KEY"
base_url = "https://ark.cn-beijing.volces.com/api/v3"
model = "doubao-seed-1-6-251015"

           # {
                #     "type": "input_image",
                #     "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png"
                # },

def query_llm(question, system_prompt=None, image_path=None):
    client = OpenAI(
        base_url= base_url,
        api_key=api_key,
    )

    # 准备消息列表
    messages = []
    
    # 如果提供了系统提示，添加到消息列表
    if system_prompt:
        messages.append({
            "role": "system",
            "content": [{
                "type": "input_text",
                "text": system_prompt
            }]
        })
    
    # 准备输入内容
    content = [
        {
            "type": "input_text",
            "text": question
        }
    ]
    
    # 如果提供了图片路径，添加图片输入
    if image_path and os.path.exists(image_path):
        # 读取本地图片并转换为base64编码
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        
        # 获取图片文件扩展名
        image_ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        
        # 添加图片内容到输入
        content.append({
            "type": "input_image",
            "image_url": f"data:image/{image_ext};base64,{base64_image}"
        })
    
    # 添加用户消息
    messages.append({
        "role": "user",
        "content": content
    })
    
    # 调用大模型API
    response = client.responses.create(
        model=model,
        input=messages
    )

    # 解析结果
    # 解析响应，同时提取CoT（思考过程）和最终回答内容
    cot_text = None
    answer_text = None
    if response.status == 'completed' and response.output:
        # 遍历output列表
        for item in response.output:
            # 提取CoT（思考过程）- reasoning类型的输出
            if item.type == 'reasoning' and hasattr(item, 'summary'):
                for summary_item in item.summary:
                    if hasattr(summary_item, 'type') and summary_item.type == 'summary_text':
                        cot_text = summary_item.text
            
            # 提取最终回答 - message类型的输出
            elif item.type == 'message' and hasattr(item, 'content'):
                for content_item in item.content:
                    if hasattr(content_item, 'type') and content_item.type == 'output_text':
                        answer_text = content_item.text
        
    return cot_text, answer_text

if __name__=='__main__':
    # # 示例1：仅文本输入
    # q1 = """
    # 请基于 "小", "鸟", "跑", "步", "大", "笑" 这6个汉字，生成一个简单的句子。
    # """
    # cot1, answer1 = query_llm(q1)
    # print("\n=== 示例1：仅文本输入 ===")
    # print("思考过程：", cot1)
    # print("最终回答：", answer1)

    # 示例2：文本+图片输入（请替换为您本地的图片路径）
    # 注意：需要确保图片文件存在，且API支持该图片格式
    # 取消注释并替换为实际的图片路径和问题
    q2 = "请描述这张图片的内容"
    image_path = "/Users/chiyuanzhang/test-bank3.png"  # 替换为实际图片路径
    if os.path.exists(image_path):
        cot2, answer2 = query_llm(q2, image_path)
        print("\n=== 示例2：文本+图片输入 ===")
        print("思考过程：", cot2)
        print("最终回答：", answer2)
    else:
        print("\n=== 示例2：文本+图片输入 ===")
        print("图片文件不存在，请检查路径是否正确")