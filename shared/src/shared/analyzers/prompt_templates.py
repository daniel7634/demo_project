"""
提示詞模板模組
提供結構化的 LLM 提示詞模板，用於生成競品分析報告
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

# 設定 logger
logger = logging.getLogger(__name__)


class PromptTemplate:
    """
    提示詞模板類別
    提供各種分析場景的提示詞模板
    """

    def __init__(self):
        """初始化提示詞模板"""
        self.templates = {
            "competitor_analysis": self._get_competitor_analysis_template(),
            "market_analysis": self._get_market_analysis_template(),
        }

    def build_competitor_analysis_prompt(self, analysis_data: Dict[str, Any]) -> str:
        """
        構建競品分析提示詞

        Args:
            analysis_data: 分析資料

        Returns:
            str: 完整的提示詞
        """
        main_product = analysis_data.get("main_product", {})
        competitors = analysis_data.get("competitors", [])
        comparison_metrics = analysis_data.get("comparison_metrics", {})
        parameters = analysis_data.get("analysis_parameters", {})

        # 構建產品資訊部分
        main_product_info = self._format_product_info(main_product, "主產品")
        logger.debug(f"主產品資訊: {main_product_info}")
        competitors_info = self._format_competitors_info(competitors)
        logger.debug(f"競品資訊: {competitors_info}")
        # 構建比較分析部分
        comparison_info = self._format_comparison_info(comparison_metrics)
        logger.debug(f"比較分析資訊: {comparison_info}")
        # 構建分析參數部分
        parameters_info = self._format_parameters_info(parameters)
        logger.debug(f"分析參數資訊: {parameters_info}")
        # 組合完整提示詞
        prompt = f"""
# 競品分析報告生成任務

## 分析資料

### {main_product_info}

### 競品資訊
{competitors_info}

### 比較分析
{comparison_info}

### 分析參數
{parameters_info}

## 報告要求

請根據以上資料生成一份專業的競品分析報告，報告應包含以下結構：

### 1. 執行摘要
- 簡要概述主產品在市場中的表現
- 與競品的關鍵差異
- 主要發現和建議

### 2. 主產品分析
- 產品基本資訊和定位
- 當前市場表現（價格、評分、評論數、排名）
- 產品優勢和劣勢

### 3. 競品分析
- 每個競品的詳細分析
- 競品之間的比較
- 市場定位分析

### 4. 比較分析
- 價格競爭力分析
- 品質指標比較
- 市場份額評估

### 5. 市場洞察
- 市場機會識別
- 競爭威脅分析
- 消費者行為洞察

### 6. 策略建議
- 定價策略建議
- 產品改進建議
- 市場定位建議
- 競爭策略建議

### 7. 風險評估
- 主要風險因素
- 風險緩解策略

## 格式要求

1. 使用 Markdown 格式
2. 包含適當的表格和圖表描述
3. 使用專業的商業分析術語
4. 提供具體的數據支撐
5. 建議要具體可執行
6. 報告長度控制在 2000-3000 字

## 注意事項

- 基於提供的數據進行客觀分析
- 避免主觀臆測，以數據為準
- 提供可操作的建議
- 保持專業和客觀的語調
- 如有數據不足，請明確說明

請開始生成報告：
"""

        return prompt.strip()

    def _format_product_info(self, product: Dict[str, Any], title: str) -> str:
        """格式化產品資訊"""
        logger.debug(f"格式化產品資訊: {product}")
        asin = product.get("asin", "未知")
        title_text = product.get("title", "未知產品")
        categories = product.get("categories", [])  # 使用實際的 categories 欄位
        metrics = product.get("current_metrics", {})

        # 安全格式化評論數
        review_count = metrics.get("review_count", "N/A")
        if isinstance(review_count, (int, float)) and review_count != "N/A":
            review_count_formatted = f"{review_count:,}"
        else:
            review_count_formatted = str(review_count)

        # 安全格式化 BSR 排名
        bsr_rank = metrics.get("bsr_rank", "N/A")
        if bsr_rank is None:
            bsr_rank = "N/A"

        info = f"""
**{title}**
- **ASIN**: {asin}
- **產品名稱**: {title_text}
- **分類**: {', '.join(categories) if categories else '未知'}

**當前指標**:
- 價格: ${metrics.get('price', 'N/A')}
- 評分: {metrics.get('rating', 'N/A')}/5.0
- 評論數: {review_count_formatted}
- BSR 排名: {bsr_rank}
- 快照日期: {metrics.get('snapshot_date', 'N/A')}
"""

        return info.strip()

    def _format_competitors_info(self, competitors: List[Dict[str, Any]]) -> str:
        """格式化競品資訊"""
        if not competitors:
            return "無競品資料"

        info_parts = []
        for i, competitor in enumerate(competitors, 1):
            asin = competitor.get("asin", "未知")
            title = competitor.get("title", "未知產品")
            categories = competitor.get("categories", [])
            metrics = competitor.get("current_metrics", {})

            # 安全格式化評論數
            review_count = metrics.get("review_count", "N/A")
            if isinstance(review_count, (int, float)) and review_count != "N/A":
                review_count_formatted = f"{review_count:,}"
            else:
                review_count_formatted = str(review_count)

            # 安全格式化 BSR 排名
            bsr_rank = metrics.get("bsr_rank", "N/A")
            if bsr_rank is None:
                bsr_rank = "N/A"

            competitor_info = f"""
**競品 {i}**
- **ASIN**: {asin}
- **產品名稱**: {title}
- **分類**: {', '.join(categories) if categories else '未知'}
- **價格**: ${metrics.get('price', 'N/A')}
- **評分**: {metrics.get('rating', 'N/A')}/5.0
- **評論數**: {review_count_formatted}
- **BSR 排名**: {bsr_rank}
"""
            info_parts.append(competitor_info.strip())

        return "\n\n".join(info_parts)

    def _format_comparison_info(self, comparison_metrics: Dict[str, Any]) -> str:
        """格式化比較分析資訊"""
        if not comparison_metrics or "error" in comparison_metrics:
            return "比較資料不足"

        price_comp = comparison_metrics.get("price_comparison", {})
        rating_comp = comparison_metrics.get("rating_comparison", {})
        review_comp = comparison_metrics.get("review_comparison", {})
        total_competitors = comparison_metrics.get("total_competitors", 0)

        # 安全格式化評論數
        def safe_format_number(value, default="N/A"):
            if isinstance(value, (int, float)) and value != "N/A" and value is not None:
                return f"{value:,}"
            return str(default)

        info = f"""
**價格比較**:
- 主產品價格: ${price_comp.get('main_price', 'N/A')}
- 競品平均價格: ${price_comp.get('avg_competitor_price', 'N/A')}
- 價格範圍: ${price_comp.get('min_competitor_price', 'N/A')} - ${price_comp.get('max_competitor_price', 'N/A')}
- 價格位置: {price_comp.get('price_position', 'unknown')}

**評分比較**:
- 主產品評分: {rating_comp.get('main_rating', 'N/A')}/5.0
- 競品平均評分: {rating_comp.get('avg_competitor_rating', 'N/A')}/5.0
- 評分範圍: {rating_comp.get('min_competitor_rating', 'N/A')} - {rating_comp.get('max_competitor_rating', 'N/A')}
- 評分位置: {rating_comp.get('rating_position', 'unknown')}

**評論數比較**:
- 主產品評論數: {safe_format_number(review_comp.get('main_reviews', 'N/A'))}
- 競品平均評論數: {safe_format_number(review_comp.get('avg_competitor_reviews', 'N/A'))}
- 評論數範圍: {safe_format_number(review_comp.get('min_competitor_reviews', 'N/A'))} - {safe_format_number(review_comp.get('max_competitor_reviews', 'N/A'))}
- 評論數位置: {review_comp.get('review_position', 'unknown')}

**分析範圍**: 共 {total_competitors} 個競品
"""

        return info.strip()

    def _format_parameters_info(self, parameters: Dict[str, Any]) -> str:
        """格式化分析參數資訊"""
        window_size = parameters.get("window_size", 7)
        analysis_date = parameters.get("analysis_date", datetime.now().isoformat())
        total_products = parameters.get("total_products", 0)
        competitor_count = parameters.get("competitor_count", 0)

        info = f"""
- **分析時間窗口**: {window_size} 天
- **分析日期**: {analysis_date}
- **總產品數**: {total_products}
- **競品數量**: {competitor_count}
"""

        return info.strip()

    def _get_competitor_analysis_template(self) -> str:
        """獲取競品分析模板"""
        return """
# 競品分析報告模板

## 1. 執行摘要
[簡要概述主產品在市場中的表現，與競品的關鍵差異，主要發現和建議]

## 2. 主產品分析
[產品基本資訊和定位，當前市場表現，產品優勢和劣勢]

## 3. 競品分析
[每個競品的詳細分析，競品之間的比較，市場定位分析]

## 4. 比較分析
[價格競爭力分析，品質指標比較，市場份額評估]

## 5. 趨勢分析
[價格趨勢變化，評分和評論趨勢，排名變化趨勢]

## 6. 市場洞察
[市場機會識別，競爭威脅分析，消費者行為洞察]

## 7. 策略建議
[定價策略建議，產品改進建議，市場定位建議，競爭策略建議]

## 8. 風險評估
[主要風險因素，風險緩解策略]
"""

    def _get_market_analysis_template(self) -> str:
        """獲取市場分析模板"""
        return """
# 市場分析報告模板

## 1. 市場概況
[市場規模、增長趨勢、主要參與者]

## 2. 競爭格局
[競爭者分析、市場份額、競爭強度]

## 3. 消費者分析
[目標客群、消費行為、需求趨勢]

## 4. 機會與威脅
[市場機會、競爭威脅、外部環境因素]

## 5. 策略建議
[市場進入策略、競爭策略、發展建議]
"""

    def get_template(self, template_name: str) -> str:
        """
        獲取指定模板

        Args:
            template_name: 模板名稱

        Returns:
            str: 模板內容
        """
        return self.templates.get(template_name, "")

    def list_templates(self) -> List[str]:
        """
        列出所有可用模板

        Returns:
            List[str]: 模板名稱列表
        """
        return list(self.templates.keys())


# 測試函數
def test_prompt_templates():
    """測試提示詞模板功能"""
    logger.info("開始測試提示詞模板...")

    try:
        template = PromptTemplate()

        # 測試資料
        test_analysis_data = {
            "main_product": {
                "asin": "B0DG3X1D7B",
                "title": "測試主產品",
                "brand": "測試品牌",
                "category": "電子產品",
                "current_metrics": {
                    "price": 99.99,
                    "rating": 4.5,
                    "review_count": 1500,
                    "bsr": 1000,
                },
            },
            "competitors": [
                {
                    "asin": "B08XYZ1234",
                    "title": "競品 1",
                    "brand": "競品品牌 1",
                    "current_metrics": {
                        "price": 89.99,
                        "rating": 4.3,
                        "review_count": 1200,
                        "bsr": 1500,
                    },
                }
            ],
            "comparison_metrics": {
                "price_comparison": {
                    "main_price": 99.99,
                    "avg_competitor_price": 89.99,
                    "min_competitor_price": 89.99,
                    "max_competitor_price": 89.99,
                    "price_position": "higher",
                },
                "rating_comparison": {
                    "main_rating": 4.5,
                    "avg_competitor_rating": 4.3,
                    "min_competitor_rating": 4.3,
                    "max_competitor_rating": 4.3,
                    "rating_position": "higher",
                },
                "review_comparison": {
                    "main_reviews": 1500,
                    "avg_competitor_reviews": 1200,
                    "min_competitor_reviews": 1200,
                    "max_competitor_reviews": 1200,
                    "review_position": "higher",
                },
                "total_competitors": 1,
            },
            "analysis_parameters": {
                "window_size": 7,
                "analysis_date": datetime.now().isoformat(),
                "total_products": 2,
                "competitor_count": 1,
            },
        }

        # 測試提示詞生成
        logger.info("測試提示詞生成...")
        prompt = template.build_competitor_analysis_prompt(test_analysis_data)
        logger.info(f"提示詞生成完成，長度: {len(prompt)} 字元")

        # 測試模板列表
        logger.info("測試模板列表...")
        templates = template.list_templates()
        logger.info(f"可用模板: {templates}")

        # 測試單個模板獲取
        logger.info("測試模板獲取...")
        competitor_template = template.get_template("competitor_analysis")
        logger.info(f"競品分析模板長度: {len(competitor_template)} 字元")

        logger.info("提示詞模板測試完成！")

    except Exception as e:
        logger.error(f"測試失敗: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    test_prompt_templates()
