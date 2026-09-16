"""
反编译能力封装。

将 androguard.decompiler 的方法封装为返回 dict 的函数，
便于 JSON 序列化和 CLI 输出。
"""

from __future__ import annotations

from typing import Union

from loguru import logger


def decompile_class(dex_list, analysis_obj, class_name: str) -> dict:
    """
    反编译指定类。

    :param dex_list: DEX 对象列表
    :param analysis_obj: Analysis 对象
    :param class_name: 类名（格式如 Lcom/example/MyClass;）
    :return: 反编译结果
    """
    for dex_obj in dex_list:
        cls = dex_obj.get_class(class_name)
        if cls is not None:
            try:
                source = cls.get_source()
                return {
                    "class": class_name,
                    "source": source if source else "",
                }
            except Exception as e:
                return {
                    "class": class_name,
                    "error": f"Decompilation failed: {str(e)}",
                }

    return {"class": class_name, "error": "Class not found in DEX"}


def decompile_method(
    dex_list, analysis_obj, class_name: str, method_name: str
) -> dict:
    """
    反编译指定方法。

    :param dex_list: DEX 对象列表
    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param method_name: 方法名
    :return: 反编译结果
    """
    # 先找到方法
    for dex_obj in dex_list:
        cls = dex_obj.get_class(class_name)
        if cls is None:
            continue

        for method in cls.get_methods():
            if method.get_name() == method_name:
                try:
                    # 获取 MethodAnalysis
                    method_analysis = analysis_obj.get_method_analysis(method)
                    if method_analysis is not None:
                        # 直接使用 DvMethod 进行反编译
                        # 注意：DecompilerDAD.get_source_method() 有 bug，
                        # 它调用 analysis.get_method(MethodAnalysis) 但该方法
                        # 期望 EncodedMethod 参数，导致返回 None。
                        # 我们直接使用底层的 DvMethod 来绕过。
                        from androguard.decompiler.decompile import DvMethod

                        dv = DvMethod(method_analysis)
                        dv.process()
                        source = dv.get_source()
                        return {
                            "class": class_name,
                            "method": method_name,
                            "descriptor": method.get_descriptor(),
                            "source": source if source else "",
                        }
                    else:
                        # 降级：获取方法的字节码
                        return {
                            "class": class_name,
                            "method": method_name,
                            "descriptor": method.get_descriptor(),
                            "source": "",
                            "note": "MethodAnalysis not found, "
                            "source unavailable",
                        }
                except Exception as e:
                    return {
                        "class": class_name,
                        "method": method_name,
                        "descriptor": method.get_descriptor(),
                        "error": f"Decompilation failed: {str(e)}",
                    }

    return {
        "class": class_name,
        "method": method_name,
        "error": "Method not found",
    }


def decompile_method_ast(
    dex_list, analysis_obj, class_name: str, method_name: str
) -> dict:
    """
    反编译指定方法并返回结构化 AST（而非纯文本源码）。

    与 decompile_method（返回文本源码）的区别：本命令用 DvMethod.process(doAST=True)
    + get_ast() 返回嵌套 AST 字典（含 triple/flags/ret/params/comments/body），
    body 是可程序化遍历的 AST 节点（如 MethodInvocation/IfStatement 等），
    适合自动检测特定代码模式、方法调用分析、控制流提取。

    :param dex_list: DEX 对象列表
    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param method_name: 方法名
    :return: 方法 AST
    """
    from androguard.decompiler.decompile import DvMethod

    for dex_obj in dex_list:
        cls = dex_obj.get_class(class_name)
        if cls is None:
            continue
        for method in cls.get_methods():
            if method.get_name() != method_name:
                continue
            try:
                method_analysis = analysis_obj.get_method_analysis(method)
                if method_analysis is None:
                    return {
                        "class": class_name,
                        "method": method_name,
                        "descriptor": method.get_descriptor(),
                        "error": "MethodAnalysis not found",
                    }
                dv = DvMethod(method_analysis)
                dv.process(doAST=True)
                ast = dv.get_ast()
                return {
                    "class": class_name,
                    "method": method_name,
                    "descriptor": method.get_descriptor(),
                    "ast": ast if ast is not None else {},
                }
            except Exception as e:
                return {
                    "class": class_name,
                    "method": method_name,
                    "descriptor": method.get_descriptor(),
                    "error": f"AST decompilation failed: {str(e)}",
                }
    return {
        "class": class_name,
        "method": method_name,
        "error": "Method not found",
    }


def decompile_method_tokens(
    dex_list,
    analysis_obj,
    class_name: str,
    method_name: str,
    limit: int = None,
) -> dict:
    """
    反编译指定方法并返回 token 流（带词法类型的源码表示）。

    与 decompile_method（纯文本）和 method-ast（AST）的区别：本命令用
    DvMethod.get_source_ext() 返回 token 列表，每项是 (token_type, value)
    二元组（如 ('NEWLINE', '\\n')、('IDENTIFIER', 'onCreate')），
    适合词法级分析、精确源码片段定位。

    :param dex_list: DEX 对象列表
    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param method_name: 方法名
    :param limit: 返回 token 数量限制
    :return: token 流
    """
    from androguard.decompiler.decompile import DvMethod

    for dex_obj in dex_list:
        cls = dex_obj.get_class(class_name)
        if cls is None:
            continue
        for method in cls.get_methods():
            if method.get_name() != method_name:
                continue
            try:
                method_analysis = analysis_obj.get_method_analysis(method)
                if method_analysis is None:
                    return {
                        "class": class_name,
                        "method": method_name,
                        "descriptor": method.get_descriptor(),
                        "error": "MethodAnalysis not found",
                    }
                dv = DvMethod(method_analysis)
                dv.process()
                tokens = dv.get_source_ext() or []
                total = len(tokens)
                if limit:
                    tokens = tokens[:limit]
                # 序列化 token：每项是 (type, value)
                token_list = [
                    {
                        "type": str(t[0]),
                        "value": str(t[1]) if len(t) > 1 else "",
                    }
                    for t in tokens
                    if isinstance(t, (list, tuple))
                ]
                return {
                    "class": class_name,
                    "method": method_name,
                    "descriptor": method.get_descriptor(),
                    "total": total,
                    "returned": len(token_list),
                    "tokens": token_list,
                }
            except Exception as e:
                return {
                    "class": class_name,
                    "method": method_name,
                    "descriptor": method.get_descriptor(),
                    "error": f"Token decompilation failed: {str(e)}",
                }
    return {
        "class": class_name,
        "method": method_name,
        "error": "Method not found",
    }


def decompile_class_ast(
    dex_list,
    analysis_obj,
    class_name: str,
    fields_limit: int = None,
    methods_limit: int = None,
) -> dict:
    """
    反编译指定类并返回类级结构化 AST（含所有方法和字段的 AST）。

    与 decompile_method_ast（单方法 AST）和 decompile class（纯文本源码）的区别：
    本命令用 DvClass.process(doAST=True) + get_ast() 一次返回类级 AST dict
    （含 rawname/name/super/flags/isInterface/interfaces/fields/methods），
    fields 是字段 AST 列表、methods 是方法 AST 列表（每项含 triple/flags/ret/
    params/comments/body），适合批量自动检测类内代码模式。

    :param dex_list: DEX 对象列表
    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param fields_limit: 返回字段 AST 数量上限（None=全部；类级 AST 可能很大，
        限制 fields/methods 数量可避免输出过大）
    :param methods_limit: 返回方法 AST 数量上限（None=全部）
    :return: 类级 AST
    """
    from androguard.decompiler.decompile import DvClass

    for dex_obj in dex_list:
        cls = dex_obj.get_class(class_name)
        if cls is None:
            continue
        try:
            dv = DvClass(cls, analysis_obj)
            dv.process(doAST=True)
            ast = dv.get_ast()
            if ast is None:
                return {"class": class_name, "ast": {}}
            # 应用 limit：截断 fields/methods 列表，保留总数
            fields = ast.get("fields") or []
            methods = ast.get("methods") or []
            fields_total = len(fields)
            methods_total = len(methods)
            if fields_limit is not None:
                ast["fields"] = fields[:fields_limit]
            if methods_limit is not None:
                ast["methods"] = methods[:methods_limit]
            ast["fields_total"] = fields_total
            ast["methods_total"] = methods_total
            return {
                "class": class_name,
                "ast": ast,
            }
        except Exception as e:
            return {
                "class": class_name,
                "error": f"Class AST decompilation failed: {str(e)}",
            }
    return {"class": class_name, "error": "Class not found in DEX"}


def decompile_class_tokens(
    dex_list, analysis_obj, class_name: str, limit: int = None
) -> dict:
    """
    反编译指定类并返回类级 token 流（结构化词法表示）。

    与 decompile class-ast（类级 AST）和 decompile class（纯文本源码）的区别：
    本命令用 DvClass.get_source_ext() 返回类级 token 列表，每项是 (类别, [子token])，
    类别有 PACKAGE（包声明）/PROTOTYPE（类声明）/FIELD（字段）/METHOD（方法）等，
    子 token 含词法类型（如 PROTOTYPE_ACCESS/NAME_FIELD/FIELD_TYPE），适合类级词法
    分析、精确源码片段定位。与 method-tokens（单方法 token）对称。

    :param dex_list: DEX 对象列表
    :param analysis_obj: Analysis 对象
    :param class_name: 类名
    :param limit: 返回顶层 token 数量上限（默认全部）
    :return: 类级 token 流
    """
    from androguard.decompiler.decompile import DvClass

    for dex_obj in dex_list:
        cls = dex_obj.get_class(class_name)
        if cls is None:
            continue
        try:
            dv = DvClass(cls, analysis_obj)
            dv.process()
            tokens = dv.get_source_ext() or []
            total = len(tokens)
            if limit:
                tokens = tokens[:limit]

            def _ser_subtoken(t):
                # 子 token 可能是 (type, value) 或 (type, value, extra...) 或嵌套 list
                if isinstance(t, (list, tuple)):
                    out = []
                    for item in t:
                        if isinstance(item, (list, tuple)):
                            # 递归序列化，过滤不可序列化对象（如 EncodedField）
                            out.append(_ser_subtoken(item))
                        elif isinstance(item, str):
                            out.append(item)
                        else:
                            out.append(str(item))
                    return out
                return str(t)

            token_list = []
            for t in tokens:
                if isinstance(t, (list, tuple)) and len(t) >= 1:
                    category = str(t[0])
                    sub = t[1] if len(t) > 1 else []
                    token_list.append(
                        {
                            "category": category,
                            "tokens": (
                                _ser_subtoken(sub)
                                if isinstance(sub, (list, tuple))
                                else str(sub)
                            ),
                        }
                    )
                else:
                    token_list.append({"raw": str(t)})
            return {
                "class": class_name,
                "total": total,
                "returned": len(token_list),
                "tokens": token_list,
            }
        except Exception as e:
            return {
                "class": class_name,
                "error": f"Class token decompilation failed: {str(e)}",
            }
    return {"class": class_name, "error": "Class not found in DEX"}
