# IPA-DN-PyNeko-v1
#
# Copyright (c) 2021- IPA CyberLab.
# All Rights Reserved.
#
# Author: Daiyuu Nobori
# Description

import os
import json
import subprocess
import inspect
from typing import List, Tuple, Dict, Set
import typing

from submodules.IPA_DN_PyNeko.v1.PyNeko import *


# res = EasyExec.ShellExecutePiped("sleep 5", ignoreError=True, timeoutSecs=6)

# print("code = " + str(res.ExitCode))

# lines = res.StdOutAndErr.splitlines()
# for line in lines:
#     print(F"# {line}")

#res = Docker.RunDockerCommand(["image", "ls"])
#print(Json.ObjectToJson(res, skipKeys=True))

# From: https://stackoverflow.com/questions/15476983/deserialize-a-json-string-to-an-object-in-python
def from_json(data, cls):
    annotations: dict = cls.__annotations__ if hasattr(
        cls, '__annotations__') else None

    if isinstance(cls, typing._GenericAlias):
        baseClass = cls.__origin__
        if issubclass(baseClass, List):
            # List 型である
            listType = cls.__args__[0]
            instance = list()
            for value in data:
                instance.append(from_json(value, listType))
            return instance
        elif issubclass(baseClass, Dict):
            # Dict 型である
            keyType = cls.__args__[0]
            valueType = cls.__args__[1]
            instance = dict()
            for key, value in data.items():
                print(f"key={key}, keyType={keyType}, value={value}, valueType={valueType}, from_json(key, keyType) = {from_json(key, keyType)}, from_json(value, valueType) = {from_json(value, valueType)}")
                instance[from_json(key, keyType)] = from_json(value, valueType)
            return instance
        else:
            typeName = baseClass.__name__
            raise Err(f"Unsupported generics: {typeName}")

    elif issubclass(cls, list):
        list_type = cls.__args__[0]
        instance: list = list()
        for value in data:
            instance.append(from_json(value, list_type))
        return instance
    elif issubclass(cls, Dict):
        key_type = cls.__args__[0]
        val_type = cls.__args__[1]
        instance: dict = dict()
        for key, value in data.items():
            instance[from_json(key, key_type)] = from_json(value, val_type)
        return instance
    else:
        # 指定された型のクラスのインスタンスを生成する
        instance: cls = cls()

        if Util.IsPrimitive(instance):
            # プリミティブな単一の値である
            return data

        # 入力される JSON データの項目を列挙する
        for name, value in data.items():
            # 列挙された項目と同じ名前のアノテーションが存在するかどうか検索する
            field_type = annotations.get(name)
            print(field_type)
            
            if not field_type:
                # アノテーションが見つからない
                setattr(instance, name, value)
            else:
                if inspect.isclass(field_type) and isinstance(value, (dict, tuple, list, set, frozenset)) and not isinstance(field_type, typing._GenericAlias):
                    # アノテーションによると、型はクラスのインスタンスである
                    print(
                        F"0: name = {name}, field_type = {field_type}, value = {value}, inspect.isclass(field_type) = {inspect.isclass(field_type)}, isinstance(field_type, typing._GenericAlias) = {isinstance(field_type, typing._GenericAlias)}")
                    setattr(instance, name, from_json(value, field_type))
                elif isinstance(field_type, typing._GenericAlias):
                    # アノテーションによると、型は Generics のインスタンスである
                    setattr(instance, name, from_json(value, field_type))

                else:
                    # アノテーションによると、型は str, int 等の普通の型である
                    print(
                        F"1: name = {name}, field_type = {field_type}, typename(field_type) = {Util.GetTypeName(field_type)}, value = {value}, inspect.isclass(field_type) = {inspect.isclass(field_type)}, isinstance(field_type, typing._GenericAlias) = {isinstance(field_type, typing._GenericAlias)}")
                    setattr(instance, name, value)
                    
        return instance


class TestClass4:
    Str5: str
    Int6: int


class TestClass3:
    Str1: str
    Int2: int
    Tc4: TestClass4
    List1: List[TestClass4]
    Dict1: Dict[str, TestClass4]


t3 = TestClass3()

t3.Str1 = "Hello"
t3.Int2 = 123
t3.Tc4 = TestClass4()
t3.Tc4.Str5 = "Dog"
t3.Tc4.Int6 = 456

t3.Dict1 = dict()

t3.List1 = []

x = TestClass4()
x.Str5 = "Super"
x.Int6 = 122333

t3.List1.append(x)

t3.Dict1["a"] = x

x = TestClass4()
x.Str5 = "Mario"
x.Int6 = 5963

t3.List1.append(x)
t3.Dict1["b"] = x

print(t3.__annotations__)

Print(t3)

jstr = Json.ObjectToJson(t3)

obj = from_json(json.loads(jstr), TestClass3)

obj: TestClass3 = obj

Print("--- obj ---")
Print(Util.GetTypeName(obj))
Print(Util.GetTypeName(obj.List1))
Print(Util.GetTypeName(obj.List1[0]))
Print(obj)

exit()


class TestClass2:
    def __init__(self):
        self.Str3 = "Neko"


class TestClass1:
    __getattr__ = dict.get

    def __init__(self):
        super().__init__()
        self.Str1 = "Hello"
        self.Int2 = 123
        self.Object3 = None


t1 = TestClass1()
t1.__setitem__("x", 123)

print(t1)
#t1.Object3 = TestClass2()

#s = json.dumps(t1, default=lambda x: x.__dict__ if Util.IsClass(x) else x)
#print(s)

s = Json.ObjectToJson(t1)
Print(s)

o = Json.JsonToData(s)
Print(o)
