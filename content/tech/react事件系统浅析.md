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
本文通过对React事件系统和源码进行浅析，回答了“为什么React需要自己实现一套事件系统？”和“React的事件系统是怎么运作起来的？”两个问题。React为了性能和复用，采用了事件代理，池，批量更新，跨浏览器和跨平台兼容等思想，实现了自己一套事件系统。React将事件监听挂载在document上，并且构造合成事件，并且在内部模拟了一套捕获和冒泡并触发回调函数的机制。

## 开始

- 如果你只有几分钟，


最近在使用React对腾讯问卷前端进行重构的时候，自己和同事遇到了一些奇怪的问题。所以花了一些时间对React源码进行了研究，此篇的主题为React事件系统，并尽量剔除复杂的技术细节，希望能以简单直观的方法回答两个问题，分别是**“为什么React需要自己实现一套事件系统？”**和**“React的事件系统是怎么运作起来的？”**。

> Stuff can sometimes get surprisingly messy if you don’t know how it works…


## 两个简单的例子

### 例子一

1. 根据下面代码，点击按钮之后，输出结果会是什么？(ABCD排序)

2. 如果我把`innerClick`中的`e.stopPropagation()`加上，输出结果又会是什么？(ABCD排序)

<a href="https://codesandbox.io/s/14vwm6jw44" target="_blank">
  <img alt="Edit React事件冒泡例子" src="https://codesandbox.io/static/img/play-codesandbox.svg">
</a>


```js
class App extends React.Component {
  innerClick = e => {
    console.log("A: react inner click.");
    // e.stopPropagation();
  };

  outerClick = () => {
    console.log("B: react outer click.");
  };

  componentDidMount() {
    document
      .getElementById("outer")
      .addEventListener("click", () => console.log("C: native outer click"));

    window.addEventListener("click", () =>
      console.log("D: native window click")
    );
  }

  render() {
    return (
      <div id="outer" onClick={this.outerClick}>
        <button id="inner" onClick={this.innerClick}>
          BUTTON
        </button>
      </div>
    );
  }
}

ReactDOM.render(<App />, document.getElementById("root"));
```

正确答案是(防止你们偷看，请向左滑动 <——   )：

```shell
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

这是一个表单，预期为你需要点击按钮edit之后才可以进行编辑，并且此时Edit按钮变为submit按钮，点击submit按钮提交表单。

<a href="https://codesandbox.io/s/yj0z7169l9" target="_blank">
  <img alt="Edit yj0z7169l9" src="https://codesandbox.io/static/img/play-codesandbox.svg">
</a>

但实际上我们发现，点击edit按钮的时候就已经触发form的submit事件了。为什么我们点击了一个`type="button"`的按钮会触发`submit`事件呢？


带着对这两个例子的思考，我们进入到本文的主题。[我只想直接看答案？](#例子debug)

## React为什么要自己实现一个事件系统？

![react事件ppt.004](https://qncdnssl.lzane.com/2018-11-04-react%E4%BA%8B%E4%BB%B6ppt.004.jpeg)

我认为这个问题主要是为了**性能**和**复用**两个方面来考虑。

首先对于性能来说，React作为一套View层面的框架，通过渲染得到vDOM，再由diff算法决定DOM树那些结点需要新增、替换或修改，假如直接在DOM结点插入原生事件监听，则会导致频繁的调用`addEventListener`和`removeEventListener`，造成性能的浪费。所以React采用了**事件代理**的方法，对于大部分事件[^propagation_document]而言都在document上做监听，然后根据Event中的target来判断事件触发的结点。

其次React合成的`SyntheticEvent`采用了**池**的思想，从而达到节约内存，避免频繁的创建和销毁事件对象的目的。这也是如果我们需要异步使用一个`syntheticEvent`，需要执行`event.persist()`才能防止事件对象被释放会池子里。

最后在React源码中随处可见batch做**批量更新**，基本上凡是可以批量处理的事情（最普遍的`setState`）React都会将中间过程保存起来，留到最后面才flush掉。就如浏览器对DOM树进行Style，Layout，Paint一样，都不会在操作`ele.style.color='red';`之后马上执行，只会将这些操作打包起来并最总在需要渲染的时候再做渲染。

```js
ele.style.color='red'; 
ele.style.color='blue';
ele.style.color='red';
浏览器只会渲染一次
```

而对于复用来说，React看到在不同的浏览器和平台上，用户界面上的事件其实非常相似，例如普通的`click`，`change`等等。React希望通过封装一层事件系统，将不同平台的原生事件都封装成`SyntheticEvent`。

- 使得**不同平台只需要通过加入EventEmitter就能使用相同的一个事件系统**，WEB平台上加入`ReactBrowserEventEmitter`，Native上加入`ReactNativeEventEmitter`。如下图，对于不同平台，React只需要替换掉左边部分，而右边`EventPluginHub`部分可以保持复用。
- 而**对于不同的浏览器而言，React帮我们做了浏览器的兼容**，例如对于`transitionEnd`,`webkitTransitionEnd`,`MozTransitionEnd`和`oTransitionEnd`, React都会集合成`topAnimationEnd`，所以我们只用处理这一个标准的事件即可。

![react事件ppt.005](https://qncdnssl.lzane.com/2018-11-04-react%E4%BA%8B%E4%BB%B6ppt.005.jpeg)

简单而言，就与jQuery帮助我们解决了不同浏览器之间的兼容问题，React更进一步，还帮我们统一了不同平台的兼容。

## React的事件系统是怎么运作起来的？

### 事件绑定

我们来看一下我们在jsx中写的`onClick` handler是怎么被记录到DOM结点上，并且在`document`上做监听的。

![](https://qncdnssl.lzane.com/2018-11-04-15413164011795.jpg)

React对于大部分事件的绑定都是使用`trapBubbledEvent`和`trapCapturedEvent`这两个函数来注册的。如上图所示，当我们执行了`render`或者`setState`之后，React的Fiber调度系统会在最后commit到DOM树之前执行`trapBubbledEven`或`trapCapturedEvent`，
通过执行`addEventListener`在document结点上绑定对应的`dispatch`作为handler负责监听类型为`topLevelType`的事件。

这里面的`dispatchInteractiveEvent`和`dispatchEvent`两个回调函数的区别为，React16开始换掉了原本Stack Reconciliation成Fiber希望实现异步渲染（目前仍未默认打开，仍需使用`unstable_`开头的api，此特性与例子2有关，将在文章最后配图解释），所以异步渲染的情况下加入我点了两次按钮，那么第二次按钮响应的时候，可能第一次按钮的handlerA中会调用`setState`，去掉这个按钮的handlerA，这是需要把第一次按钮的结果先给flushed掉并commit到DOM树，才能够保持一致性，这个时候就会用到`dispatchInteractiveEvent`。可以理解成`dispatchInteractiveEvent`在执行前都会确保之前所有操作都已最总commit到DOM树，再开始自己的流程，并最总触发`dispatchEvent`。但由于目前React仍是同步渲染的，所以这两个函数在目前的表现是一致的，希望React17会带给我们默认打开的异步渲染功能。

到现在我们已经在document结点上监听了事件了，现在需要来看如何将我们在jsx中写的handler存起来对应到相应的结点上。

在我们每次新建或者更新结点时，React最终会调用`createInstance`或者`commitUpdate`这两个函数，而这两个函数都会最终调用`updateFiberProps`这个函数，将`props`也就是我们的`onClick`，`onChange`等handler给存到DOM结点上。

至此，我们我们已经在document上监听了事件，并且将handler存在对应DOM结点。接下来需要看React怎么最终去接受浏览器的原生事件并最终触发对应的handler了。

### 事件触发

> 这里我做了个动画，希望能够对你们理解有帮助。看过这个动画，如果你对源码部分不感兴趣，那可以直接跳到[例子debug](#例子debug)部分

<iframe src="https://www.lzane.com/animate/react-event-system/index.html" style="border:0; width:100%; height:500px; overflow:hidden"></iframe>

以简单的`click`事件为例，通过事件绑定我们已经在`document`上监听了`click`事件，当我们真正点击了这个按钮的时候，原生的事件是如果进入React的管辖范围的？如何合成`SyntheticEvent`以及如何模拟捕获和冒泡的？以及最后我们在jsx中写的`onClick`handler是如何被最终触发的？带着这些问题，我们一起来看一下事件触发阶段。

我会大概用下图这种方式来解析代码，左边是我点击一个绑定了`handleClick`的按钮后的js调用栈，右边是每一步的代码，均已删除部分不影响理解的代码。希望通过这种方式能使大家更易了解React的事件触发机制。

![](https://qncdnssl.lzane.com/2018-11-04-15413164315532.jpg)

当我们点击一个按钮是，`click`事件将会最终冒泡至document，并触发我们监听在document上的handler `dispatchEvent`，接着触发`batchedUpdates`。`batchedUpdates`这个格式的代码在React的源码里面会频繁的出现，基本上React将所有能够**批量处理**的事情都会先收集起来，再一次性处理。

可以看到默认的`isBatching`是false的，当调用了一次`batchedUpdates`，`isBatching`的值将会变成true，此时如果在接下来的调用中有继续调用`batchedUpdates`的话，就会直接执行`handleTopLevel`,直到调用栈重新回到第一次调用`batchedUpdates`的时候，才会将所有结果一起flush掉（更新到dom上）。

![](https://qncdnssl.lzane.com/2018-11-04-15413175673832.jpg)

有的同学可能问调用栈中的`BatchedUpdates$1`是什么？或者浏览器的renderer和Native的renderer是如果挂在到React的事件系统上的?

其实React事件系统里面提供了一个函数`setBatchingImplementation`，用来动态挂载不同平台的renderer，这个也体现了React事件系统的`复用`。

![](https://qncdnssl.lzane.com/2018-11-04-15413164501870.jpg)

`handleTopLevel`会调用`runExtractedEventsInBatch()`,这是React事件处理最重要的函数，如上面动画我们看到的，在`EventEmitter`里面做的事，其实主要就是这个函数的两点。

- **第一点是根据原生事件合成合成事件，并且在vDom上模拟捕获冒泡，收集所有需要执行的事件回调。**
- **第二点是遍历回调数组，触发回调函数。**

![](https://qncdnssl.lzane.com/2018-11-04-15413164560026.jpg)

首先调用`extractEvents`，传入原生事件`e`，React事件系统根据可能的事件插件合成合成事件`Synthetic e`。 这里我们可以看到调用了`EventConstructor.getPooled()`，从事件池中去除合成事件，如果事件池为空，则新创建一个合成事件，这体现了React为了性能实现了**池**的思想。

![](https://qncdnssl.lzane.com/2018-11-04-15413164608984.jpg)

然后传入Propagator，在Fiber tree上模拟捕获和冒泡，并收集所有需要执行的事件回调和对应的结点。`traverseTwoPhase`模拟了捕获和冒泡的两个阶段，这里实现很巧妙，简单而言就是正向和反向遍历了一下数组。接着对每一个结点，调用`listenerAtPhase`取出事件绑定时挂载在结点上的回调函数，把它加入回调数组中。

![](https://qncdnssl.lzane.com/2018-11-04-15413164659157.jpg)

接着遍历所有合成事件。这里可以看到当一个事件处理完的时候，React会调用`event.isPersistent()`来查看这个合成事件是否需要被持久化，如果不需要就会释放这个合成事件，这也就是为什么当我们需要异步读取操作一个合成事件的时候，需要执行`event.persist()`，不然React就是在这里释放掉这个事件。

![](https://qncdnssl.lzane.com/2018-11-04-15413164725789.jpg)

最后这里就是回调函数被真正触发的时候了，取出回调数组`event._dispatchListeners`，遍历触发回调函数。并通过`event.isPropagationStopped()`这一步来模拟停止冒泡。这里我们可以看到，React在收集回调数组的时候并不会去管我们时候调用了`stopPropagation`，而是会在触发的阶段才会去检查是否需要停止冒泡。

至此，一个事件回调函数就被触发了，里面如果执行了`setState`等就会等到调用栈弹回到最低部的`interactiveUpdate`中的被最终flush掉，构造vDOM，和好，并最终被commit到DOM上。这就是事件触发的整个过程了，可以回去再看一下[动画](#事件触发)，相信你会更加理解这个过程的。

## 例子Debug

我们对React事件系统已经比较熟悉了，现在回到文章开头的那两个玄学问题，我们来看一下到底为什么?

### 例子一

> 如果想看题目内容或者忘记题目了，可以点击[这里](#例子一)查看。

相信看完这篇文章，如果你已经对React事件系统有所理解，这道题应该是不难了。

1. 因为React事件监听是挂载在document上的，所以原生系统在`#outer`上监听的回调`B`会最先被执行；接着原生事件冒泡至document进入React事件系统，React事件系统模拟捕获冒泡输出`A`和`B`；最后React事件系统执行完毕回到浏览器继续冒泡到window，输出`D`。
2. 原生系统在`#outer`上监听的回调`B`会最先被执行；接着原生事件冒泡至document进入React事件系统，在React事件处理中`#inner`调用了`stopPropagation`，事件被停止冒泡。

所以，最好**不要混用React事件系统和原生事件系统**，如果混用了，请保证你知道会发生什么。

### 例子二

> 如果想看题目内容或者忘记题目了，可以点击[这里](#例子二)查看。

这个问题就稍微复杂一点。首先我们点击`edit`按钮浏览器触发一个`click`事件，冒泡至document进入React事件系统，React执行回调调用`setState`，此时React事件系统对事件的处理执行完毕。由于目前React是同步渲染的，所以接着React执行`performSyncWork`将该button改成`type="submit"`,由于同个位置的结点并且tag都为button，所以React复用了这个button结点[^react_reconciliation],并更新到DOM上。此时浏览器对`click`事件执行继续，其发现该结点的`type="submit"`,则触发`submit`事件。

解决的办法就有很多种了，给button加上`key`；两个按钮分开写，不要用三元等都可以解决问题。

具体可以看一下下面的这个调用图，应该也很好理解，如果有不能理解的地方，请在下面留言，我会尽我所能解释清楚。

![](https://qncdnssl.lzane.com/2018-11-04-15413164911702.jpg)

-----------

#### 额外多说一个点，“setState是异步的”

相信对于很多React开发者来说，“setState是异步的”这句话应该经常听到，我记得我一开始学习React的时候经常就会看到这句话，然后说如果需要用到之前的state需要在setState中采用`setState((preState)=>{})`这样的方式。

但其实这句话并不是完全准确的。准确的说法应该是**setState有时候是异步的，setState相对于浏览器而言是同步的**

目前而言`setState`在生命周期以及事件回调中是异步的，也就是会收集起来批量处理。在其它情况下如promise，setTimeout中都是同步执行的，也就是调用一次setState就会render一次并更新到DOM上面，不信的话可以点击[这里](https://codesandbox.io/s/pyqmrx516x)。

且在JS调用栈被弹空时候，必定是已经将结果更新到DOM上面了（同步渲染）。这也就是setState相对于浏览器是同步的含义。如下图所示

![](https://qncdnssl.lzane.com/2018-11-04-15413204706161.jpg)

异步渲染的流程图大概如下图所示，最近一次思考这个问题的时候，发现如果现在是异步渲染的话，那我们的例子二将变成偶现的坑😂

![](https://qncdnssl.lzane.com/2018-11-04-15413165006172.jpg)

不过React团队已经为异步渲染的愿景开发了两年，React16中已经采用了Fiber reconciliation和提供了异步渲染的api `unstable_`,相信在React17中我们可以享受到异步渲染带来的性能提升，感谢React团队。


## 总结
希望读完此文，能对你React事件系统有个简单的认识。知道“为什么React需要自己实现一套事件系统？”和“React的事件系统是怎么运作起来的？”。React为了**性能**和**复用**，采用了事件代理，池，批量更新，跨浏览器和跨平台兼容等思想，实现了自己一套事件系统。React将事件监听挂载在document上，并且构造合成事件，并且在内部模拟了一套捕获和冒泡并触发回调函数的机制。

如果你还有哪里不清楚，发现文章有错漏，或者单纯的交流相关问题，请在下面留言，我会尽我所能回复和解答你的疑问的。 如果你喜欢我的文章，请关注我和我的博客，谢谢。

## Read More & Reference
- [推荐！React events in depth w/ Kent C. Dodds, Ben Alpert, & Dan Abramov](https://www.youtube.com/watch?v=dRo_egw7tBc&t=8s) 
- [推荐！The React and React Native Event System Explained: A Harmonious Coexistence](https://levelup.gitconnected.com/how-exactly-does-react-handles-events-71e8b5e359f2)
- [Didact Fiber: Incremental reconciliation](https://engineering.hexacta.com/didact-fiber-incremental-reconciliation-b2fe028dcaec)
- [Codebase Overview](https://reactjs.org/docs/codebase-overview.html)

[^propagation_document]:除了少数不会冒泡到document的事件，例如video等。
[^react_reconciliation]:[具体原因可以参考](https://reactjs.org/docs/reconciliation.html#motivation)
