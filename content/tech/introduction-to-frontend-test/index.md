---
title: "我“码”由我不由天：谈谈前端测试的作用和实践"
date: 2019-09-01T08:00:00+08:00
draft: false
tags:
- Tech
- Frontend
- Test
slug: introduction-to-frontend-test
---

## 引入
忙碌了大半年，好不容易有机会跟老板要到一次休假机会，开开心心的带着女朋友飞到了马来西亚。你们俩坐在拥有世界最美夕阳的丹绒亚路海滩上，等待着落日的到来，一个多么浪漫的场景。

突然你的电话响了，公司测试的同学告诉你说你负责的一个页面出了bug，需要紧急修复。没办法你只能掏出电脑去修复这个bug，不一会儿你发现这个bug其实很好修复你很快就修复完了，正当你以为可以结束这个事的时候。你被告知**“由于你修复了这个bug，引入了其他另外两个bug”**

没办法你只能继续修复，周围的气氛也在微微的变化，如果你还是没法在短时间内修复，下场可能就是...

(!! 这里要有个动画)

## 前端测试的分类
一般来说我们会将前端测试分成三类:

- 单元测试(Unit Tests)：对一个最小单元例如一个函数，一个类，通过确认它的输入输出来保证表现是符合预期的。
- 集成测试(Intergration Tests)：一系列单元组合在一起表现是否符合预期，一般包括副作用。
- 端对端测试(E2E Tests)：在真实的浏览器环境中，通过编写自动化脚本，保证功能正常。

![几种测试的对比](./test_compare.png)

单元测试是成本最低，速度最快的，这里说的成本低包括开发维护成本低，运行所需要的算力低。一般来说单元测试和集成测试都是可以在开发阶段给开发人员提供实时反馈的。而端对端测试则成本最高，运行速度最慢，因为端对端测试需要真实的运行环境，浏览器环境，以及网络请求等等，所以其没法在开发阶段给开发人员提供实时反馈。

那么可能有同学会问，既然单元测试是成本最低，速度最快的，那我们是不是可以**只写单元测试，而不去使用集成测试和端对端测试?**

**答案肯定是不行的**

(!! 动图要加文字)
![只有单元测试的情况](./unit_test_only.gif)

也就是说，单元测试->集成测试->端对端测试，可以覆盖的问题面越广，能够覆盖的点就越多。

## 前端测试的作用

### 消除恐惧，提升信心

### 帮助代码做重构优化

### 开发阶段实时反馈

### 时间更有价值

## 前端测试的实践

## 前端测试经常问到的问题

## 参考
- 【书籍】Refactoring: Improving the Design of Existing Code (2nd Edition) by Martin Fowler
- 【书籍】Clean Code: A Handbook of Agile Software Craftsmanship by Robert C. Martin
- [【文章】 An Overview of JavaScript Testing in 2019 ]( https://medium.com/welldone-software/an-overview-of-javascript-testing-in-2019-264e19514d0a )
- [【课程】JavaScript Testing Practices and Principles by Kent C. Dodds]( https://frontendmasters.com/courses/testing-practices-principles/ )