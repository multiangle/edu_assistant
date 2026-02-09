import pandas as pd
import random
import numpy as np
from datetime import datetime, timedelta
import re
from llm import query_llm
import json

# 设置OpenAI API密钥（请替换为您自己的密钥）

def read_word_table(file_path="data.xlsx"):
    """
    读取字表数据
    :param file_path: 字表文件路径
    :return: 包含字表数据的DataFrame
    """
    try:
        df = pd.read_excel(file_path, sheet_name="字")
        # 确保必要的列存在
        required_columns = ["内容", "级别", "出现次数", "正确次数", "准确率"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"字表中缺少必要的列: {col}")
        
        # 如果缺少最近出现时间列，添加该列
        if "最近出现时间" not in df.columns:
            df["最近出现时间"] = datetime.now().strftime("%Y-%m-%d")
        
        return df
    except Exception as e:
        print(f"读取字表时出错: {e}")
        return None

def calculate_days_since_last_appearance(last_date):
    """
    计算距离上次出现的天数
    :param last_date: 上次出现时间，格式为字符串 "YYYY-MM-DD"或datetime对象
    :return: 距离今天的天数
    """
    try:
        # 如果是float类型，可能是NaN，返回默认值
        if isinstance(last_date, float):
            return 30  # 默认30天
        
        # 如果是datetime对象，直接使用
        if isinstance(last_date, datetime):
            last = last_date
        else:
            # 尝试解析字符串
            last = datetime.strptime(str(last_date), "%Y-%m-%d")
            
        today = datetime.now()
        return (today - last).days
    except Exception as e:
        print(f"计算天数时出错: {e}")
        return 30  # 默认30天

def extract_words(df, num_words=50):
    """
    根据准确率和最近出现天数抽取指定数量的汉字
    :param df: 字表数据
    :param num_words: 要抽取的汉字数量
    :return: 抽取的汉字列表
    """
    # 计算每个字的采样权重
    df_copy = df.copy()
    
    # 处理空准确率（出现次数为0的情况）
    df_copy["准确率"] = df_copy["准确率"].fillna(0)
    
    # 计算距离上次出现的天数
    df_copy["距上次出现天数"] = df_copy["最近出现时间"].apply(calculate_days_since_last_appearance)
    
    # 计算采样权重：准确率越低，天数越长，权重越高
    # 权重公式：(1 - 准确率) * (1 + 距上次出现天数/30)
    df_copy["权重"] = (1 - df_copy["准确率"]) * (1 + df_copy["距上次出现天数"] / 30)
    
    # 归一化权重
    total_weight = df_copy["权重"].sum()
    if total_weight == 0:
        # 如果所有权重为0，均匀采样
        df_copy["权重"] = 1
        total_weight = len(df_copy)
    
    df_copy["归一化权重"] = df_copy["权重"] / total_weight
    
    # 根据权重无放回采样
    # 使用numpy的choice函数，设置replace=False实现无放回采样
    sampled_indices = np.random.choice(
        df_copy.index.tolist(),
        size=min(num_words, len(df_copy)),
        replace=False,
        p=df_copy["归一化权重"].tolist()
    )
    
    # 获取采样的汉字
    sampled_words = df_copy.loc[sampled_indices, "内容"].tolist()
    
    return sampled_words

def generate_phrases_and_sentences(chars, num_phrases=3, num_sentences=2):
    """
    调用大模型为每个汉字生成词语和短句
    :param chars: 汉字列表
    :param num_phrases: 每个字生成的词语数量
    :param num_sentences: 每个字生成的短句数量
    :return: 生成的词语和短句列表
    """
    results = []
    
    # 构建提示词
    system_prompt = "你是一个幼儿教育专家，擅长为汉字生成简单的词语和短句，帮助幼儿认字。生成的内容要简单易懂，适合3-6岁幼儿学习。"
    char_txt = '、'.join(chars)
    user_prompt = f"请基于以下汉字 [{char_txt}] 生成{num_phrases}个词语和{num_sentences}个短句。每个词语或句子占一行，不要添加任何序号或标点符号。"
    # 调用llm.py中的query_llm函数
    try:
        cot_text, answer_text = query_llm(user_prompt, system_prompt)
            
        # 提取生成的内容
        if answer_text:
            generated_content = answer_text.strip()
            results.extend(generated_content.split("\n"))
    except Exception as e:
        print(f"调用大模型时出错: {e}")
    
    # 去重并过滤空行
    results = [line.strip() for line in results if line.strip()]
    unique_results = []
    seen = set()
    for line in results:
        if line not in seen:
            seen.add(line)
            unique_results.append(line)
    
    return unique_results

def format_output(content):
    """
    格式化输出内容。根据content中的单词和短句，将内容填充起来。一行最多10个字。如果当前行<=5个字，则再加内容。单词之间用空格分隔。
    :param content: 生成的内容列表
    :return: 格式化后的内容字符串
    """
    # 移除空内容
    content = [item.strip() for item in content if item.strip()]
    if not content:
        return ""
    
    # 计算每个词的汉字数量
    word_lengths = []
    for item in content:
        item_chars = re.findall(r'[\u4e00-\u9fa5]', item)
        word_lengths.append(len(item_chars))
    
    formatted = ""
    i = 0
    n = len(content)
    
    while i < n:
        current_line = []
        current_length = 0
        
        # 尝试填充当前行，确保不超过10个字
        while i < n:
            next_length = current_length + word_lengths[i]
            
            if next_length <= 10:
                # 如果添加这个词不会超过10个字，就添加
                current_line.append(content[i])
                current_length = next_length
                i += 1
            else:
                # 检查当前行是否<=5个字，如果是且不是最后一行，我们需要调整策略
                if current_length <= 5 and i < n:
                    # 如果当前行太短且还有更多内容，我们必须添加这个词，即使会超过10个字
                    # 这样可以避免单行字数<=5的情况
                    current_line.append(content[i])
                    current_length = next_length
                    i += 1
                break
        
        # 将当前行添加到结果中
        formatted += " ".join(current_line) + "\n\n"
    
    return formatted.strip()

def check_content(content, selected_words, word_table, new_ratio=0.2, add_new_words=True):
    """
    检查生成的内容，确保大部分字来自选中的字，并添加新字到字表
    :param content: 生成的内容列表
    :param selected_words: 选中的字列表
    :param word_table: 原始字表
    :param new_ratio: 新字比例阈值
    :param add_new_words: 是否添加新字到字表
    :return: 更新后的字表和过滤后的内容列表
    """
    # 计算每个词的新字比例
    word_new_ratios = []
    all_chinese_chars = []
    all_new_chars = []
    
    # 遍历每个词，计算新字比例
    for word in content:
        # 提取当前词的所有汉字
        chinese_chars_in_word = re.findall(r'[\u4e00-\u9fa5]', word)
        if not chinese_chars_in_word:
            continue
        
        # 统计当前词的新字数量
        new_chars_in_word = [char for char in chinese_chars_in_word if char not in selected_words]
        new_ratio_in_word = len(new_chars_in_word) / len(chinese_chars_in_word) if chinese_chars_in_word else 0
        
        # 记录当前词的新字比例
        word_new_ratios.append((word, new_ratio_in_word))
        
        # 累积所有汉字和新字
        all_chinese_chars.extend(chinese_chars_in_word)
        all_new_chars.extend(new_chars_in_word)
    
    # 计算整体新字比例
    overall_new_ratio = len(all_new_chars) / len(all_chinese_chars) if all_chinese_chars else 0
    print(f"生成内容整体新字比例: {overall_new_ratio:.2f}")
    
    # 过滤内容：如果整体新字比例高于阈值，则只保留新字比例低于阈值的词
    filtered_content = []
    if overall_new_ratio > new_ratio:
        print(f"整体新字比例高于阈值 {new_ratio}，开始过滤内容...")
        for word, ratio in word_new_ratios:
            if ratio <= new_ratio:
                filtered_content.append(word)
    else:
        # 整体新字比例低于阈值，保留所有内容
        filtered_content = [word for word, _ in word_new_ratios]
    
    print(f"过滤后保留的内容数量: {len(filtered_content)} / {len(content)}")
    
    # 统计过滤后内容中的所有字
    all_text_filtered = "".join(filtered_content)
    chinese_chars_filtered = re.findall(r'[\u4e00-\u9fa5]', all_text_filtered)
    
    # 统计每个字的出现次数
    char_counts = {}
    for char in chinese_chars_filtered:
        char_counts[char] = char_counts.get(char, 0) + 1
    
    # 添加新字到字表
    updated_table = word_table.copy()
    if add_new_words:
        for char in char_counts:
            if char not in updated_table["内容"].tolist():
                # 新增字，级别默认0，出现次数0，正确次数0，准确率0，最近出现时间为今天
                new_row = {
                    "内容": char,
                    "级别": 0,
                    "出现次数": 0,
                    "正确次数": 0,
                    "准确率": 0,
                    "最近出现时间": datetime.now().strftime("%Y-%m-%d")
                }
                updated_table = pd.concat([updated_table, pd.DataFrame([new_row])], ignore_index=True)
    
    return updated_table, filtered_content

def recognize_photo_results(photo_path):
    """
    识别拍照结果，返回每个字的识别结果
    :param photo_path: 拍照结果图片路径
    :return: 识别结果列表，格式如["小(1)鸟(0)", "跑(0)步(1)"]
    """
    # 这里需要实现图片识别功能
    # 由于没有实际的图片识别API，这里返回模拟数据
    # 实际实现时，需要使用OCR识别文字，然后识别圈和叉
    
    system_prompt = "你是一个幼儿教育专家，擅长为汉字生成简单的词语和短句，识别认字的拍照结果"
    question = """分析一下图片,里面是一张认字和对应结果表格。每行里面有单词和短句,下面一行代表了上面行每个字的识字结果。答对的画圈,答错的画叉。你要做的是识别里面字和对应的识别结果,然后按单词输出。答对的输出1,答错的输出0.识别不了的就输出-1. 例如：
小(1)鸟(0)
跑(0)步(1)
大(1)笑(-1)

注意:圈和叉有些是小孩画的,不那么标准,你要注意识别。里面只有2种结果,不是圈就是叉。
输出内容严格按照上面示例来，不要乱加其他符号
    """

    cot, content = query_llm(question, system_prompt, image_path=photo_path)
    
    # 将结果转换为列表格式
    if content:
        # 按行分割并过滤空行
        result_list = [line.strip() for line in content.split('\n') if line.strip()]
        return result_list
    else:
        return []

def update_word_table(results, word_table):
    """
    更新字表的统计信息
    :param results: 识别结果列表，格式如["小(1)", "鸟(0)"]
    :param word_table: 当前字表
    :return: 更新后的字表
    """
    updated_table = word_table.copy()
    today = datetime.now().strftime("%Y-%m-%d")
    bayes_value = 5
    # 解析识别结果
    for line in results:
        # 提取每个字及其结果
        word_results = re.findall(r'([\u4e00-\u9fa5])\((-?\d+)\)', line)
        for word, result in word_results:
            result = int(result)
            if result != -1:  # 只更新能识别的结果
                # 查找字在表中的位置
                idx = updated_table.index[updated_table["内容"] == word].tolist()
                if idx:
                    idx = idx[0]
                    # 更新出现次数
                    updated_table.loc[idx, "出现次数"] += 1
                    # 更新正确次数
                    if result == 1:
                        updated_table.loc[idx, "正确次数"] += 1
                    # 更新准确率（使用贝叶斯平滑）
                    # 贝叶斯平滑：(正确次数 + 1) / (出现次数 + 2)
                    updated_table.loc[idx, "准确率"] = (updated_table.loc[idx, "正确次数"] + bayes_value) / (updated_table.loc[idx, "出现次数"] + bayes_value + 1)
                    # 更新最近出现时间
                    updated_table.loc[idx, "最近出现时间"] = today
    
    return updated_table

def check_res(photo_path_list):
    """
    识别小朋友认字的结果，更新字表数据
    :param photo_path_list: 照片路径列表
    :return: 更新后的字表
    """
    # 1. 读取现有的字表
    word_table = read_word_table()
    if word_table is None:
        print("无法读取字表，更新失败")
        return None
    
    # 2. 识别所有照片的结果
    all_results = []
    for i, photo_path in enumerate(photo_path_list):
        print(f"正在识别照片: {photo_path}")
        results = recognize_photo_results(photo_path)
        print(f"照片的识别结果:")
        for r in results:
            print(r)
        if results:
            # 直接添加识别结果列表到总结果中
            all_results.extend(results)
    
    # 3. 过滤空行和无效行
    all_results = [line.strip() for line in all_results if line.strip()]
    
    if not all_results:
        print("没有识别到有效结果")
        return word_table
    
    # 4. 按字统计所有识别结果
    char_stats = {}
    for line in all_results:
        # 提取每个字及其结果
        word_results = re.findall(r'([\u4e00-\u9fa5])\((-?\d+)\)', line)
        for char, result in word_results:
            result = int(result)
            if result != -1:  # 只统计能识别的结果
                if char not in char_stats:
                    char_stats[char] = {"出现次数": 0, "正确次数": 0}
                char_stats[char]["出现次数"] += 1
                if result == 1:
                    char_stats[char]["正确次数"] += 1
    print("结果汇总：")
    print(json.dumps(char_stats, ensure_ascii=False, indent=2))
    
    # 5. 汇总后更新字表
    updated_table = word_table.copy()
    today = datetime.now().strftime("%Y-%m-%d")
    bayes_value = 5
    
    for char, stats in char_stats.items():
        # 查找字在表中的位置
        idx = updated_table.index[updated_table["内容"] == char].tolist()
        if idx:
            idx = idx[0]
            # 更新出现次数和正确次数
            updated_table.loc[idx, "出现次数"] += stats["出现次数"]
            updated_table.loc[idx, "正确次数"] += stats["正确次数"]
            # 更新准确率（使用贝叶斯平滑）
            updated_table.loc[idx, "准确率"] = (updated_table.loc[idx, "正确次数"] + 1) / (updated_table.loc[idx, "出现次数"] + 2)
            # 更新最近出现时间
            updated_table.loc[idx, "最近出现时间"] = today
    
    # 6. 保存更新后的字表
    save_word_table(updated_table)
    
    print(f"成功处理 {len(photo_path_list)} 张照片，字表已更新")
    print(f"共统计 {len(char_stats)} 个汉字的识别结果")
    return updated_table

def gene_content(num_words=50, num_phrases=3, num_sentences=2, save_to_file=False, output_file="generated_content.txt"):
    """
    根据字表生成测试内容。功能流程如下：
    1. 从字表进行采样
    2. 根据采到的字生成单词和短句
    3. 按照格式输出
    
    :param num_words: 要采样的汉字数量
    :param num_phrases: 每个字生成的词语数量
    :param num_sentences: 每个字生成的短句数量
    :param save_to_file: 是否将生成的内容保存到文件
    :param output_file: 保存生成内容的文件路径
    :return: 格式化后的生成内容
    """
    try:
        # 1. 读取字表
        print("正在读取字表...")
        word_table = read_word_table()
        if word_table is None:
            print("无法读取字表，生成内容失败")
            return None

        # 2. 从字表采样汉字
        print("正在从字表采样汉字...")
        selected_words = extract_words(word_table, num_words=num_words)
        print(f"采样的汉字: {selected_words}")
        
        # 3. 根据采到的字生成单词和短句
        print("正在生成词语和短句...")
        generated_content = generate_phrases_and_sentences(selected_words, num_phrases=num_phrases, num_sentences=num_sentences)
        
        if not generated_content:
            print("生成内容失败")
            return None
        
        # 4. 检查生成内容并更新字表（调整顺序到格式化输出之前）
        print("\n正在检查生成内容并更新字表...")
        updated_table, filtered_content = check_content(generated_content, selected_words, word_table)
        save_word_table(updated_table)
        
        # 5. 格式化输出（使用过滤后的内容）
        print("正在格式化输出...")
        formatted_content = format_output(filtered_content)
        print("\n生成的测试内容:")
        print(formatted_content)
        
        # 6. 保存到文件（如果需要）
        if save_to_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(formatted_content)
                print(f"\n生成的内容已保存到 {output_file}")
            except Exception as e:
                print(f"\n保存生成内容到文件时出错: {e}")
        
        return formatted_content
    except Exception as e:
        print(f"生成测试内容时出错: {e}")
        return None

def save_word_table(word_table, file_path="data.xlsx"):
    """
    保存字表到Excel文件
    :param word_table: 要保存的字表
    :param file_path: 保存路径
    """
    try:
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            word_table.to_excel(writer, sheet_name="字", index=False)
        print(f"字表已成功保存到 {file_path}")
    except Exception as e:
        print(f"保存字表时出错: {e}")

def main():
    """
    主函数，协调各个功能
    """
    # 调用gene_content函数生成测试内容
    print("=== 生成测试内容 ===")
    generated_content = gene_content(num_words=50, num_phrases=30, num_sentences=10, save_to_file=True)
    
    if generated_content:
        print("\n=== 程序执行完成! ===")
    else:
        print("\n=== 生成内容失败! ===")


if __name__ == "__main__":
    main() # 生成内容

    # # # 记录结果
    # check_res(["/Users/chiyuanzhang/multiangle/花卷教育/识字/260207_res1.png",
    # "/Users/chiyuanzhang/multiangle/花卷教育/识字/260207_res2.png"])