---
title: "React事件系统浅析"
date: 2018-11-03T20:00:00+08:00
draft: true
tags:
- Tech
- Front-end
- React
---

## TL;DR

## 开始

最近在使用React对腾讯问卷前端进行重构的时候，自己和同事遇到了一些奇怪的问题。所以花了一些时间对React源码进行了研究，此篇的主题为React事件系统。希望能够通过这篇文章回答两个问题，分别是“为什么React需要自己实现一套事件系统？”和“React的事件系统是怎么运作起来的？”。

Disclaimer: 我不是专业的React项we目开发者，本文所述是建立在自己的尝试，源码阅读，以及网络上相关文章学习得到。如果有错漏的地方，还望批评指正。我也会在验证了之后更新文章。

> Stuff can sometimes get surprisingly messy if you don’t know how it works…


<div class="iframe-container">
<iframe src="http://pgfpshkce.bkt.clouddn.com/animate/react-event-trigger/index.html" style="border:0; height:600px; overflow:hidden"></iframe>
</div>


## 两个简单的例子


### 例子一

1. 根据下面代码，点击按钮之后，输出结果会是什么？

2. 如果我把`innerClick`中的`e.stopPropagation();`加上，输出结果又会是什么？

<iframe src="https://codesandbox.io/embed/14vwm6jw44?autoresize=1&expanddevtools=1&hidenavigation=1&view=split" style="width:100%; height:500px; border:0; border-radius: 4px; overflow:hidden;" sandbox="allow-modals allow-forms allow-popups allow-scripts allow-same-origin"></iframe>

正确答案是：

```
1. 
    C: native outer click 
    A: react inner click. 
    B: react outer click. 
    D: native window click 
2.
    C: native outer click 
    A: react inner click.
```

### 例子二

这是一个表单，预期为你需要点击按钮edit之后才可以进行编辑，并且此时Edit按钮变为submit按钮，点击submit按钮提交表单。但实际上我们发现，点击edit按钮的时候就已经触发form的submit事件了。可到这里尝试。

<iframe src="https://codesandbox.io/embed/yj0z7169l9?autoresize=1&expanddevtools=1&hidenavigation=1&view=split" style="width:100%; height:500px; border:0; border-radius: 4px; overflow:hidden;" sandbox="allow-modals allow-forms allow-popups allow-scripts allow-same-origin"></iframe>



## React为什么要自己实现一个事件系统？

![](media/15395196498375.jpg)

我认为这个问题主要是为了**性能**和**复用**考虑。

首先对于性能来说，React作为一套View层面的框架，通过渲染得到vDOM，再由diff算法决定DOM树那些结点需要新增、替换或修改，假如直接在DOM结点插入原生事件监听，则会导致频繁的调用`addEventListener`和`removeEventListener`，造成性能的浪费。所以React采用了**事件代理**的方法，对于大部分事件^* 而言都在document上做监听，然后根据Event中的target来判断事件触发的结点。

其次React合成的`SyntheticEvent`采用了**池**的思想，从而达到节约内存，避免频繁的创建和销毁事件对象的目的。这也是如果我们需要异步使用一个`syntheticEvent`，需要执行`event.persist()`才能防止事件对象被释放会池子里。

最后在React源码中随处可见batch做**批量更新**，基本上凡是可以批量处理的事情React都会将中间过程保存起来，留到最后面才flush掉。就如浏览器对DOM树进行Style，Layout，Paint一样，都不会在操作`ele.style.color='red';`之后马上执行，只会将这些操作,例如（`ele.style.color='red'; ele.style.color='blue'; ele.style.color='red';`）打包起来并最总在需要渲染的时候再做渲染。

上述几点在后面的篇幅中会详细介绍。

而对于复用来说，React看到在不同的浏览器和平台上，用户界面上的事件其实非常相似，例如普通的`click`，`change`等等。React希望通过封装一层事件系统，将不同平台的原生事件都封装成`SyntheticEvent`，使得不同平台只需要通过加入EventEmitter就能使用相同的一个事件系统，WEB平台上加入`ReactBrowserEventEmitter`，Native上加入`ReactNativeEventEmitter`。而对于不同的浏览器而言，React帮我们做了浏览器的兼容，例如对于`transitionEnd`,`webkitTransitionEnd`,`MozTransitionEnd`和`oTransitionEnd`, React都会集合成`topAnimationEnd`，所以我们只用处理这一个标准的事件即可。

简单而言，就与jQuery帮助我们解决了不同浏览器之间的兼容问题，React更进一步，还帮我们统一了不同平台的兼容。

------

^* 除了少数不会冒泡到document的事件，例如video等。

## 基本框架


![](media/15395196657462.jpg)


## 事件绑定

我们来看一下我们在jsx中写的`onClick` handler是怎么被记录到DOM结点上，并且在`document`上做监听的。

![](media/15395235047129.jpg)

React对于大部分事件的绑定都是使用`trapBubbledEvent`和`trapCapturedEvent`这两个函数来注册的。如上图所示，当我们执行了`render`或者`setState`之后，React的Fiber调度系统会在最后commit到DOM树之前执行`trapBubbledEven`或`trapCapturedEvent`，
通过执行`addEventListener`在document结点上绑定对应的`dispatch`作为handler负责监听类型为`topLevelType`的事件。

这里面的`dispatchInteractiveEvent`和`dispatchEvent`两个回调函数的区别为，React16开始换掉了原本Stack Reconciliation成Fiber希望实现异步渲染（目前仍未默认打开，仍需使用`unstable_`开头的api），所以异步渲染的情况下加入我点了两次按钮，那么第二次按钮响应的时候，可能第一次按钮的handlerA中会调用`setState`，去掉这个按钮的handlerA，这是需要把第一次按钮的结果先给flushed掉并commit到DOM树，才能够保持一致性，这个时候就会用到`dispatchInteractiveEvent`。可以理解成`dispatchInteractiveEvent`在执行前都会确保之前所有操作都已最总commit到DOM树，再开始自己的流程，并最总触发`dispatchEvent`。但由于目前React仍是同步渲染的，所以这两个函数在目前的表现是一致的，希望React17会带给我们默认打开的异步渲染功能。

到现在我们已经在document结点上监听了事件了，现在需要来看如何将我们在jsx中写的handler存起来对应到相应的结点上。

在我们每次新建或者更新结点时，React最终会调用`createInstance`或者`commitUpdate`这两个函数，而这两个函数都会最终调用`updateFiberProps`这个函数，将`props`也就是我们的`onClick`，`onChange`等handler给存到DOM结点上。

至此，我们我们已经在document上监听了事件，并且将handler存在对应DOM结点。接下来需要看React怎么最终去接受浏览器的原生事件并最终触发对应的handler了。

## 事件触发

以简单的`click`事件为例，通过事件绑定我们已经在`document`上监听了`click`事件，当我们真正点击了这个按钮的时候，原生的事件是如果进入React的管辖范围的？如何合成`SyntheticEvent`以及如何模拟捕获和冒泡的？以及最后我们在jsx中写的`onClick`handler是如何被最终触发的？带着这些问题，我们一起来看一下事件触发阶段。

我会大概用下图这种方式来解析代码，左边是我点击一个绑定了`handleClick`的按钮后的js调用栈，右边是每一步的代码，均已删除部分不影响理解的代码。希望通过这种方式能使大家更易了解React的事件触发机制。

![](media/15396056654375.jpg)

当我们点击一个按钮是，`click`事件将会最终冒泡至document，并触发我们监听在document上的handler `dispatchEvent`，接着触发`batchedUpdates`。`batchedUpdates`这个格式的代码在React的源码里面会频繁的出现，基本上React将所有

![react事件ppt.010](media/react%E4%BA%8B%E4%BB%B6ppt.010.jpeg)
![react事件ppt.011](media/react%E4%BA%8B%E4%BB%B6ppt.011.jpeg)
![react事件ppt.012](media/react%E4%BA%8B%E4%BB%B6ppt.012.jpeg)
![react事件ppt.013](media/react%E4%BA%8B%E4%BB%B6ppt.013.jpeg)
![react事件ppt.014](media/react%E4%BA%8B%E4%BB%B6ppt.014.jpeg)
![react事件ppt.015](media/react%E4%BA%8B%E4%BB%B6ppt.015.jpeg)


## 例子Debug

![](media/15395198063244.jpg)



## 总结

-------

- [The React and React Native Event System Explained: A Harmonious Coexistence](https://levelup.gitconnected.com/how-exactly-does-react-handles-events-71e8b5e359f2)


