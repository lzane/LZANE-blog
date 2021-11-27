---
title: "如何创造一门上万人使用的DSL"
date: 2021-10-24T8:00:00+08:00
draft: false
tags:
- Tech
- DSL
slug: create-a-dsl
---

## TL;DR;

## 简单介绍背景、照片、视频
本文是我在[2021TWEB腾讯前端技术大会](https://tweb.tencent.com/)上分享的文字稿整理，包括一门DSL（领域特定语言）落地前中后期的经验和思考，如“哪些是适合DSL落地的业务场景？”、“DSL语法应该如何设计？”、“如何实现解析器Parser？”等等。希望可以帮助大家了解DSL这一技术，在下一次遇到技术选型的时候，有更大的武器库，如果可以通过创造一门DSL帮助你的业务降本增效，那就更好了。

如果你更加倾向于从视频中学习，可以考虑购买TWEB的在线票，支持腾讯前端技术大会。

## 我们做了一个什么东西？

问卷逻辑大家应该不会陌生，比如去年疫情，我们填过很多的健康上报，那么这样一份问卷可能会在第一道题询问你的体温，如果你的体温<37.2度，那么你的问卷会很短；如果你的体温>37.2度，那么可能会有接下来很多道题询问你的症状，是否离开过本省等等。

上面举的只是个简单的例子，而像我们部门CDC，在支持公司内外专业的用户研究和市场调研时，会有很多更加复杂的定制逻辑，没法使用一种简单的交互来完成。所以，我们创造了一门DSL，像下方的动图一样，只需在左边输入好DSL，即可完成问卷逻辑的设置，在右侧预览。

![](./wj-dsl-editor.gif)

腾讯问卷的DSL支持多种自定义逻辑，目前已经帮助2万名领域专家完成了5万多份问卷的复杂逻辑设置。

![](./wj-dsl-grammar.jpg)

![](./wj-dsl-demo.png)

## 适合DSL落地的场景

## 实现DSL编译器

确定使用DSL来解决问题后，我们马上就会面临一个问题：我们如何开发一个解析器，来解析用户输入的DSL呢？

是不是我们要学习一整本恐龙书才能够做这件事？是不是我们要从头开发一个解析器？答案是不用的，计算机发展到现在，即使是我们常用的很多高级语言，也不会从头开发一个解析器，而是会使用一种叫做解析器生成器的东西。

### 解析器生成器

解析器生成器，顾名思义是它可以根据你定义好的语法，生成出对应的解析器，用以解析用户输入的DSL，而你只需要使用语法描述好你的DSL长什么样。在JS中有很多广泛使用的解析器生成器，包括`PEG.js`、`jison`、`antlr`等等，它们使用的解析算法、性能等等差异超出了本文的范畴，后面可以再开一篇文章来聊聊。

![](./parser-generator.png)

这里以`PEG.js`为例给大家简单介绍一下解析器生成器（Parser generator）,假设我们要设计一个DSL用来表达“n分钟之前”，使用JS我们会写成

```js
new Date(Date.now()-2*60*1000)
```

我们希望说可以实现一个解析器生成器，解析下方的DSL也能够得到同样的Date对象

```dsl
2 mins ago
```

我们先来看一个简单的demo

```js
const PEG = require("pegjs")
const grammar = `
Start
  = i:Integer _ "mins" _ "ago"
  
Integer "integer"
  = _ [0-9]+

_ "whitespace"
  = [ ]*
`

const parser = PEG.generate(grammar)
const result = parser.parse(process.argv[2])
console.log(result)
```

可以看到一个简单的解析器生成器包括
1. 定义好DSL的语法`grammar`
2. 调用`PEG.generate`得到一个解析器
3. 使用解析器去解析`parser.parse`用户输入的DSL

我们运行上面的代码，我们可以得到屏幕下方这样一个多维数组，它其实是个树状结构。

```bash
$ node demo.js "2 mins ago"
[ [ [], [ '2' ] ], [ ' ' ], 'mins', [ ' ' ], 'ago' ]
```

如下图，我将这个树状结构与语法中对应的语法用同样的颜色标注了出来。

![](./parser-generator-colored.jpeg)

得益于PEG.js支持在语法中内嵌JS代码来帮助我们处理一下解析时的中间状态，此时如果我们想把数组中的第0位转化成int，只需要在grammar中内嵌JS代码

```js
const PEG = require("pegjs")
const grammar = `
Start
  = i:Integer _ "mins" _ "ago"
  
Integer "integer"
  = _ [0-9]+ { 
    return parseInt(text(), 10)
  }

_ "whitespace"
  = [ ]*
`

const parser = PEG.generate(grammar)
const result = parser.parse(process.argv[2])
console.log(result)
```

当我们再次执行上面的代码，我们可以发现数组的第0位已经变成一个int了

```bash
$ node demo.js "2 mins ago"
[ 2, [ ' ' ], 'mins', [ ' ' ], 'ago' ]
```

同样的思路，我们可以通过修改grammar，让其输出一个JS的Date对象

```js
const PEG = require("pegjs")
const grammar = `
Start
  = i:Integer _ "mins" _ "ago"{
    return new Date(Date.now()-i*60*1000)
  }
  
Integer "integer"
  = _ [0-9]+ { 
    return parseInt(text(), 10)
  }

_ "whitespace"
  = [ ]*
`

const parser = PEG.generate(grammar)
const result = parser.parse(process.argv[2])
console.log(result)
```

```bash
$ node demo.js "2 mins ago"
2021-06-20T12:07:03.960Z
```

如果我们想扩充我们的解析器生成器，让其同时支持解析"x hours ago"，只需要在grammar中，加入如下规则。

```js
const PEG = require("pegjs")
const grammar = `
Start
  = i:Integer _ u:Unit _ "ago"{
    return new Date(Date.now()-i*u)
  }
  
Unit "unit"
  = "mins" {
    return 60*1000
  } 
  / "hours" {
    return 60*60*1000
  }

Integer "integer"
  = _ [0-9]+ { 
    return parseInt(text(), 10)
  }

_ "whitespace"
  = [ ]*
`

const parser = PEG.generate(grammar)
const result = parser.parse(process.argv[2])
console.log(result)
```

至此，我们学会了如何使用一个解析器生成器来生成一个解析器。

当然我们只是介绍了一些简单的语法，PEG.js实际上非常强大，它可以实现将JS代码转换成AST的工作，并且配备了一个在线的Demo，大家感兴趣的话可以到 https://pegjs.org/online 尝试（JavaScript的PEG语法： https://raw.githubusercontent.com/pegjs/pegjs/master/examples/javascript.pegjs）

### 编辑器架构

![](./parser-arch.png)

## DSL的语法设计

## DSL的配套设施

## 只需一个解析器？

## 内部DSL VS 外部DSL

## 克制

## 更进一步的学习？