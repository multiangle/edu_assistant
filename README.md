
# 儿童识字辅助系统

## 功能
 - 维护识字库：data.xlsx
 - 基于掌握不牢固的字生成学习短句和短词
 - 识别并录入学习结果(圈是正确，叉是错误)

## 用法
### 增加识字内容
在data.xlsx中增加对应的新字和级别

### 生成内容
main_v0中相关内容改成
```python

if __name__ == "__main__":
    main() # 生成内容
```

### 录入结果
main_v0中相关内容改成
```python

if __name__ == "__main__":
    # # 记录结果
    check_res(["/Users/chiyuanzhang/multiangle/花卷教育/识字/260207_res1.png",
    "/Users/chiyuanzhang/multiangle/花卷教育/识字/260207_res2.png"])
```