"""
LLM 報告生成器模組
使用 OpenAI GPT 生成競品分析報告
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import openai
from openai import OpenAI
from shared.analyzers.analyzer_types import (
    BasicComparison,
    CompetitorAnalysisResult,
    ProductCurrentData,
)
from shared.analyzers.prompt_templates import PromptTemplate
from shared.database.model_types import ProductSnapshotDict

# 設定 logger
logger = logging.getLogger(__name__)


class LLMReportGenerator:
    """
    LLM 報告生成器
    使用 OpenAI GPT 生成專業的競品分析報告
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        初始化 LLM 報告生成器

        Args:
            api_key: OpenAI API 金鑰（如果未提供則從環境變數獲取）
            model: 使用的 GPT 模型
        """
        if not openai:
            raise ImportError("OpenAI 套件未安裝")

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("未提供 OpenAI API 金鑰")

        self.model = model
        self.client = OpenAI(api_key=self.api_key)
        self.prompt_template = PromptTemplate()

        # 成本控制設定
        self.max_tokens = 4000  # 最大 token 數
        self.temperature = 0.7  # 創造性程度

        logger.info(f"LLM 報告生成器初始化完成，模型: {model}")

    def generate_report(
        self, analysis_result: CompetitorAnalysisResult, parameters: Dict[str, str]
    ) -> str:
        """
        生成競品分析報告

        Args:
            analysis_result: 競品分析結果（來自 CompetitorAnalyzer）
            parameters: 分析參數

        Returns:
            str: Markdown 格式的報告內容
        """
        try:
            logger.info(f"開始使用 {self.model} 生成報告...")

            # 準備分析資料
            analysis_data = self._prepare_analysis_data(analysis_result, parameters)

            # 構建提示詞
            prompt = self.prompt_template.build_competitor_analysis_prompt(
                analysis_data
            )

            # 調用 OpenAI API
            response = self._call_openai_api(prompt)

            # 驗證和格式化報告
            report_content = self._validate_and_format(response)

            logger.info(f"報告生成完成，長度: {len(report_content)} 字元")
            return report_content

        except Exception as e:
            logger.error(f"生成報告失敗: {str(e)}", exc_info=True)
            raise

    def _prepare_analysis_data(
        self, analysis_result: CompetitorAnalysisResult, parameters: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        準備分析資料供 LLM 使用

        Args:
            analysis_result: 競品分析結果
            parameters: 分析參數

        Returns:
            Dict[str, Any]: 格式化的分析資料
        """
        main_product_data = analysis_result.main_product_data
        competitors_data = analysis_result.competitor_data
        basic_comparison = analysis_result.basic_comparison

        # 組織主產品資料
        main_data = {
            "asin": main_product_data.basic_info.asin,
            "title": main_product_data.basic_info.title or "未知產品",
            "categories": main_product_data.basic_info.categories,
            "current_metrics": self._format_current_data_metrics(
                main_product_data.current_data
            ),
        }

        # 組織競品資料
        formatted_competitors = []
        for competitor in competitors_data:
            competitor_data = {
                "asin": competitor.basic_info.asin,
                "title": competitor.basic_info.title or "未知產品",
                "categories": competitor.basic_info.categories,
                "current_metrics": self._format_current_data_metrics(
                    competitor.current_data
                ),
            }
            formatted_competitors.append(competitor_data)

        # 使用基本比較結果
        comparison_metrics = self._format_basic_comparison(basic_comparison)

        return {
            "main_product": main_data,
            "competitors": formatted_competitors,
            "comparison_metrics": comparison_metrics,
            "analysis_parameters": {
                "window_size": int(parameters.get("window_size", "7")),
                "analysis_date": datetime.now().isoformat(),
                "total_products": len(competitors_data) + 1,
                "competitor_count": len(competitors_data),
            },
        }

    def _format_current_data_metrics(
        self, current_data: ProductCurrentData
    ) -> Dict[str, Any]:
        """
        格式化當前數據為 LLM 可用的格式

        Args:
            current_data: ProductCurrentData 物件

        Returns:
            Dict[str, Any]: 格式化的當前數據
        """
        return {
            "price": current_data.price,
            "rating": current_data.rating,
            "review_count": current_data.review_count,
            "bsr_rank": current_data.bsr,
            "bsr_details": current_data.bsr_details,
            "snapshot_date": current_data.snapshot_date,
        }

    def _format_snapshot_metrics(
        self, snapshot: Optional[ProductSnapshotDict]
    ) -> Dict[str, Any]:
        """
        格式化快照資料為 LLM 可用的格式

        Args:
            snapshot: ProductSnapshotDict 物件或 None

        Returns:
            Dict[str, Any]: 格式化的快照資料
        """
        if not snapshot:
            return {
                "price": None,
                "rating": None,
                "review_count": None,
                "bsr_rank": None,
                "bsr_details": [],
                "snapshot_date": None,
            }

        # 處理 BSR 資料（實際是陣列格式）
        bsr_info = self._extract_bsr_info_from_snapshot(snapshot.bsr_data or [])

        return {
            "price": snapshot.price,
            "rating": snapshot.rating,
            "review_count": snapshot.review_count,
            "bsr_rank": bsr_info["overall_rank"],
            "bsr_details": bsr_info["details"],
            "snapshot_date": (
                snapshot.snapshot_date.isoformat() if snapshot.snapshot_date else None
            ),
        }

    def _extract_bsr_info_from_snapshot(
        self, bsr_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        從快照的 BSR 資料中提取排名資訊

        Args:
            bsr_data: BSR 資料陣列

        Returns:
            Dict[str, Any]: 包含整體排名和詳細資訊的字典
        """
        if not bsr_data:
            return {"overall_rank": None, "details": []}

        # 提取所有排名資訊
        details = []
        overall_rank = None

        for bsr_item in bsr_data:
            rank = bsr_item.get("rank")
            category = bsr_item.get("category", "未知類別")
            raw_value = bsr_item.get("raw_value", "")

            details.append({"rank": rank, "category": category, "raw_value": raw_value})

            # 使用第一個排名作為整體排名（通常是主要類別）
            if overall_rank is None and rank is not None:
                overall_rank = rank

        return {"overall_rank": overall_rank, "details": details}

    def _format_basic_comparison(
        self, basic_comparison: BasicComparison
    ) -> Dict[str, Any]:
        """
        格式化基本比較結果為 LLM 可用的格式

        Args:
            basic_comparison: 基本比較結果

        Returns:
            Dict[str, Any]: 格式化的比較指標
        """
        return {
            "price_comparison": {
                "main_price": basic_comparison.price_comparison.main_price,
                "avg_competitor_price": basic_comparison.price_comparison.avg_competitor_price,
                "min_competitor_price": basic_comparison.price_comparison.min_competitor_price,
                "max_competitor_price": basic_comparison.price_comparison.max_competitor_price,
                "price_position": (
                    "higher"
                    if basic_comparison.price_comparison.main_price
                    and basic_comparison.price_comparison.avg_competitor_price
                    and basic_comparison.price_comparison.main_price
                    > basic_comparison.price_comparison.avg_competitor_price
                    else (
                        "lower"
                        if basic_comparison.price_comparison.avg_competitor_price
                        else "unknown"
                    )
                ),
            },
            "rating_comparison": {
                "main_rating": basic_comparison.rating_comparison.main_rating,
                "avg_competitor_rating": basic_comparison.rating_comparison.avg_competitor_rating,
                "min_competitor_rating": basic_comparison.rating_comparison.min_competitor_rating,
                "max_competitor_rating": basic_comparison.rating_comparison.max_competitor_rating,
                "rating_position": (
                    "higher"
                    if basic_comparison.rating_comparison.main_rating
                    and basic_comparison.rating_comparison.avg_competitor_rating
                    and basic_comparison.rating_comparison.main_rating
                    > basic_comparison.rating_comparison.avg_competitor_rating
                    else (
                        "lower"
                        if basic_comparison.rating_comparison.avg_competitor_rating
                        else "unknown"
                    )
                ),
            },
            "review_comparison": {
                "main_reviews": basic_comparison.review_comparison.main_review_count,
                "avg_competitor_reviews": basic_comparison.review_comparison.avg_competitor_reviews,
                "min_competitor_reviews": basic_comparison.review_comparison.min_competitor_reviews,
                "max_competitor_reviews": basic_comparison.review_comparison.max_competitor_reviews,
                "review_position": (
                    "higher"
                    if basic_comparison.review_comparison.main_review_count
                    and basic_comparison.review_comparison.avg_competitor_reviews
                    and basic_comparison.review_comparison.main_review_count
                    > basic_comparison.review_comparison.avg_competitor_reviews
                    else (
                        "lower"
                        if basic_comparison.review_comparison.avg_competitor_reviews
                        else "unknown"
                    )
                ),
            },
            "total_competitors": basic_comparison.total_competitors,
            "data_availability": {
                "main_has_data": basic_comparison.data_availability.main_has_data,
                "competitors_with_data": basic_comparison.data_availability.competitors_with_data,
            },
        }

    def _call_openai_api(self, prompt: str) -> str:
        """
        調用 OpenAI API

        Args:
            prompt: 提示詞

        Returns:
            str: API 回應內容
        """
        try:
            logger.debug(f"調用 OpenAI API，提示詞長度: {len(prompt)} 字元")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一名專業的電商分析師，擅長生成詳細的競品分析報告。請根據提供的資料生成專業、結構化的 Markdown 格式報告。",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1,
            )

            content = response.choices[0].message.content
            logger.debug(f"API 調用成功，回應長度: {len(content)} 字元")

            return content

        except Exception as e:
            logger.error(f"OpenAI API 調用失敗: {str(e)}", exc_info=True)
            raise

    def _validate_and_format(self, content: str) -> str:
        """
        驗證和格式化報告內容

        Args:
            content: 原始報告內容

        Returns:
            str: 格式化後的報告內容
        """
        try:
            # 基本清理
            content = content.strip()

            # 確保以標題開始
            if not content.startswith("#"):
                content = "# 競品分析報告\n\n" + content

            # 驗證 Markdown 格式
            content = self._fix_markdown_formatting(content)

            # 添加報告元資料
            metadata = self._add_report_metadata(content)

            return metadata + "\n\n" + content

        except Exception as e:
            logger.warning(f"報告格式化失敗: {str(e)}", exc_info=True)
            return content

    def _fix_markdown_formatting(self, content: str) -> str:
        """修復 Markdown 格式問題"""
        # 確保標題格式正確
        lines = content.split("\n")
        fixed_lines = []

        for line in lines:
            # 修復標題格式
            if (
                line.strip()
                and not line.startswith("#")
                and not line.startswith("-")
                and not line.startswith("*")
            ):
                # 如果這行看起來像標題但沒有 # 前綴，添加 #
                if len(line.strip()) < 50 and not line.strip().endswith("."):
                    line = f"## {line.strip()}"

            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def _add_report_metadata(self, content: str) -> str:
        """添加報告元資料"""
        metadata = f"""---
title: 競品分析報告
generated_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
model: {self.model}
version: 1.0
---"""
        return metadata

    def estimate_cost(self, prompt: str) -> Dict[str, Any]:
        """
        估算 API 調用成本

        Args:
            prompt: 提示詞

        Returns:
            Dict[str, Any]: 成本估算資訊
        """
        # 簡單的 token 估算（實際應該使用 tiktoken 庫）
        estimated_tokens = len(prompt.split()) * 1.3  # 粗略估算

        # GPT-3.5-turbo 定價（每 1K tokens）
        input_cost_per_1k = 0.0015  # $0.0015
        output_cost_per_1k = 0.002  # $0.002

        estimated_input_cost = (estimated_tokens * input_cost_per_1k) / 1000
        estimated_output_cost = (self.max_tokens * output_cost_per_1k) / 1000

        return {
            "estimated_tokens": int(estimated_tokens),
            "estimated_input_cost": round(estimated_input_cost, 4),
            "estimated_output_cost": round(estimated_output_cost, 4),
            "estimated_total_cost": round(
                estimated_input_cost + estimated_output_cost, 4
            ),
            "model": self.model,
        }


# 測試函數
def test_llm_report_generator():
    """測試 LLM 報告生成器功能"""
    logger.info("開始測試 LLM 報告生成器...")

    try:
        # 檢查 API 金鑰
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("未設定 OPENAI_API_KEY 環境變數，跳過測試")
            return

        # 初始化生成器
        generator = LLMReportGenerator(model="gpt-3.5-turbo")

        # 測試資料
        test_product_data = {
            "main_product": {
                "asin": "B0DG3X1D7B",
                "info": {
                    "title": "測試主產品",
                    "brand": "測試品牌",
                    "category": "電子產品",
                },
                "latest_snapshot": {
                    "price": 99.99,
                    "rating": 4.5,
                    "review_count": 1500,
                    "bsr_data": {"overall_rank": 1000},
                },
                "historical_snapshots": [],
            },
            "competitors": [
                {
                    "asin": "B08XYZ1234",
                    "info": {
                        "title": "競品 1",
                        "brand": "競品品牌 1",
                        "category": "電子產品",
                    },
                    "latest_snapshot": {
                        "price": 89.99,
                        "rating": 4.3,
                        "review_count": 1200,
                        "bsr_data": {"overall_rank": 1500},
                    },
                    "historical_snapshots": [],
                }
            ],
            "analysis_metadata": {
                "window_size": 7,
                "analysis_date": datetime.now().isoformat(),
                "total_products": 2,
                "competitor_count": 1,
            },
        }

        test_parameters = {
            "main_asin": "B0DG3X1D7B",
            "competitor_asins": ["B08XYZ1234"],
            "window_size": 7,
        }

        # 測試成本估算
        logger.info("測試成本估算...")
        prompt = generator.prompt_template.build_competitor_analysis_prompt(
            generator._prepare_analysis_data(test_product_data, test_parameters)
        )
        cost_estimate = generator.estimate_cost(prompt)
        logger.info(f"成本估算: ${cost_estimate['estimated_total_cost']}")

        # 測試報告生成（如果 API 金鑰可用）
        logger.info("測試報告生成...")
        report = generator.generate_report(test_product_data, test_parameters)
        logger.info(f"報告生成完成，長度: {len(report)} 字元")
        logger.debug(f"報告預覽:\n{report[:200]}...")

        logger.info("LLM 報告生成器測試完成！")

    except Exception as e:
        logger.error(f"測試失敗: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    test_llm_report_generator()
