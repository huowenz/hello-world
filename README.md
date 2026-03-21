# hello-world

## 本地麻将辅助算法

### 1) 手动输入版（已实现）

`mahjong_helper.py` 可离线进行：
- 手牌解析（万/筒/索/字）
- 和牌判断（标准型 + 七对子）
- 向听数计算（标准型 + 七对子）
- 14 张手牌的弃牌建议（按向听和进张数排序）

运行：

```bash
python3 mahjong_helper.py "123m456m789p11s22z"
```

---

### 2) 微信 Web 全自动版（新增）

新增 `wechat_web_auto_assistant.py`：
- 自动打开微信 Web 页面（Playwright）
- 周期截图并识别：我方手牌 + 三家牌河（OpenCV 模板匹配）
- 自动调用牌理算法输出向听与前 5 条弃牌建议

> 注意：你需要自己准备模板图片（`templates/*.png`）和区域配置文件（可从 `wechat_regions.example.json` 复制）。

#### 安装依赖

```bash
pip install playwright opencv-python
playwright install chromium
```

#### 启动方式

```bash
cp wechat_regions.example.json wechat_regions.json
python3 wechat_web_auto_assistant.py \
  --url "https://wx.qq.com" \
  --templates "./templates" \
  --config "./wechat_regions.json" \
  --interval 1.5 \
  --threshold 0.7
```


#### 你这张图的预设配置（1696x896）

我根据你发的截图做了一个可直接试跑的预设：`wechat_regions.wx_1696x896.json`。

Windows PowerShell：

```powershell
Copy-Item .\wechat_regions.wx_1696x896.json .\wechat_regions.json
python .\wechat_web_auto_assistant.py `
  --url "https://wx.qq.com" `
  --templates ".\templates" `
  --config ".\wechat_regions.json" `
  --interval 1.2 `
  --threshold 0.68
```

如果你看到：
- 手牌经常少识别/多识别：先微调 `hand_region` 的 `x/w`。
- 右/左/上家牌河识别错位：分别微调 `river_regions` 三个框。

#### 模板目录约定

模板文件名必须是牌名，例如：

- `templates/1m.png`
- `templates/9p.png`
- `templates/5s.png`
- `templates/1z.png` ~ `templates/7z.png`

#### 输出说明

每轮会打印：
- 识别到的手牌
- 三家牌河
- 向听数
- 若识别为 14 张手牌，输出前 5 条弃牌建议

---

## 免责声明

请仅用于学习/研究与本地测试。接入任何线上平台前，请先确认平台规则与当地法律法规。
