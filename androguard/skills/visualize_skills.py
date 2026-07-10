"""
可视化能力封装。

将 androguard.core.bytecode 的可视化方法封装为返回 dict 的函数，
便于 JSON 序列化和 CLI 输出。
"""

from __future__ import annotations

from typing import Union

from loguru import logger


def visualize_method_dot(method_analysis) -> dict:
    """
    导出方法的控制流图（CFG）为 DOT 格式。

    :param method_analysis: MethodAnalysis 对象
    :return: DOT 格式的 CFG
    """
    try:
        from androguard.core.bytecode import method2dot

        dot_str = method2dot(method_analysis)
        return {
            "class": method_analysis.class_name,
            "method": method_analysis.name,
            "descriptor": method_analysis.descriptor,
            "dot": dot_str,
        }
    except Exception as e:
        return {
            "class": method_analysis.class_name if method_analysis else "unknown",
            "method": method_analysis.name if method_analysis else "unknown",
            "error": f"Failed to generate DOT: {str(e)}",
        }


def visualize_method_image(method_analysis, output: str, fmt: str = "png") -> dict:
    """
    导出方法的控制流图为图片（PNG/JPG）。

    :param method_analysis: MethodAnalysis 对象
    :param output: 输出文件路径
    :param fmt: 输出格式（png, jpg）
    :return: 导出结果
    """
    try:
        from androguard.core.bytecode import method2format

        method2format(output, _format=fmt, mx=method_analysis)
        return {
            "class": method_analysis.class_name,
            "method": method_analysis.name,
            "descriptor": method_analysis.descriptor,
            "output": output,
            "format": fmt,
        }
    except Exception as e:
        return {
            "class": method_analysis.class_name if method_analysis else "unknown",
            "method": method_analysis.name if method_analysis else "unknown",
            "error": f"Failed to export image: {str(e)}",
        }


def visualize_method_json(method_analysis) -> dict:
    """
    导出方法的控制流图为 JSON 格式。

    :param method_analysis: MethodAnalysis 对象
    :return: JSON 格式的 CFG
    """
    try:
        from androguard.core.bytecode import method2json

        json_str = method2json(method_analysis)
        return {
            "class": method_analysis.class_name,
            "method": method_analysis.name,
            "descriptor": method_analysis.descriptor,
            "cfg": json_str,
        }
    except Exception as e:
        return {
            "class": method_analysis.class_name if method_analysis else "unknown",
            "method": method_analysis.name if method_analysis else "unknown",
            "error": f"Failed to generate JSON: {str(e)}",
        }
