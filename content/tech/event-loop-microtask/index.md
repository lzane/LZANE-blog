---
title: "事件循环 Microtasks 的运行时机——从接受知识到探索v8源码"
date: 2021-04-08T8:00:00+08:00
draft: false
tags:
- Tech
- v8
- 源码
slug: event-loop-microtasks
---

刚学前端那会学习事件循环，说事件循环的存在是为了解决：由于JavaScript是单线程的，所以需要事件循环来防止JS阻塞，让网络请求等I/O操作不阻塞主线程。

而Microtasks是一类优先级比较高的任务，我们不能像Macrotasks一样插入Macrotasks队列末端，等待多个事件循环后才执行，而需要插入到Microtasks的队列里面，在本次事件循环中执行。

比如下面这个有趣的例子：

```js
document.body.innerHTML = ` 
    <button id="btn" type="button">btn</button> 
`; 

const button = document.getElementById('btn')
 
button.addEventListener('click',()=>{
  Promise.resolve().then(()=>console.log('promise resolved 1'))
  console.log('listener 1')
})
 
button.addEventListener('click',()=>{
  Promise.resolve().then(()=>console.log('promise resolved 2'))
  console.log('listener 2')
})
 
// 1. 手动点击按钮 
// button.click() // 2. 解开这句注释，用JS触发点击行为
```

当我手动点击按钮的时候，浏览器的输出是下面的A还是B？

- A. listener1 -> promise resolved 1 -> listener2 -> promise resolved 2 
- B. listener1 -> listener2 -> promise resolved 1 -> promise resolved 2

大家可以在这里试一下

[![Edit naughty-morning-9hnr3](https://codesandbox.io/static/img/play-codesandbox.svg)](https://codesandbox.io/s/naughty-morning-9hnr3?fontsize=14&hidenavigation=1&theme=dark)

当我将上面代码中的最后一行注释打开，使用JS触发点击行为的时候，浏览器的输出是A还是B？

大家觉的上面1、2两种情况的输出顺序是否一样？

答案非常有意思

- 当我们使用1. 手动点击按钮时，浏览器的输出是A
- 当我们使用2. 用JS触发点击行为时，浏览器的输出是B

# 接受大佬的知识

那为什么会出现这种情况呢？ 这个Microtasks的运行时机有关。 两年前当我带着这个问题搜索资料并询问大佬的时，大佬告诉我：

**当浏览器JS引擎调用栈弹空的时候，就会运行Microtasks**

按照这个结论，我使用Chrome Devtool中的Performance做了一次探索

## 人工点击按钮

人工点击的时候输出为 listener1 -> promise resolved 1 -> listener2 -> promise resolved 2 。 

![img.png](img.png)

- 从上图中我们可以看到，一次点击事件之后，浏览器会调用Function Call进入JS引擎，执行listener1，输出`listener1`。
- 弹栈时发现JS调用栈为空，这时候就会执行Microtasks队列中的所有Microtask，输出`promise resolved 1`。
- 接着浏览器调用Function Call进入JS引擎，执行listener2，输出`listener 2`。
- 弹栈时发现JS调用栈为空，这时候就会执行Microtasks队列中的所有Microtask，输出`promise resolved 2`。

## JS触发点击事件

在JS代码中触发点击时输出为 listener1 -> listener2 -> promise resolved 1 -> promise resolved 2

![img_1.png](img_1.png)

- 从上图中我们可以看到，浏览器运行JS代码时，调用了button.click这个函数
- 进入事件处理，执行listener1，输出`listener1`。
- 弹栈时发现JS调用栈非空（button.click函数还在）
- 执行listener2，输出`listener 2`。
- 弹栈时发现JS调用栈为空，这时候就会执行Microtasks队列中的所有Microtask，输出`promise resolved 1`、`promise resolved 2`。

> Tips:
> 
> Chrome Devtool 中的Performance是一个sample profiler (采样分析仪)，即它的运行机制是每1ms暂停一下vm，将当前的调用栈记录下来，最后利用这部分信息做出可视化。由于它是一种sample的机制，所以在两个sample之间的运行状态可能会被丢失，所以我们在使用这个工具的时候可以
> 
> 1. 使CPU变慢：在Devtool中打开CPU 6x slowdown
> 2. 在要探索的函数中执行一段比较长的for循环占用CPU时间（如上面的heavy）

# 探索V8源码

两年的时间过去了，在上周整理笔记的时候，我开始质疑这一个知识**当浏览器JS引擎调用栈弹空的时候，就会运行Microtasks**，因为这其实是个表现，我想知道浏览器和JS引擎到底是怎么实现这样的机制的。

> 下面探索基于Chrome Version 88.0.4324.192 (Official Build) (x86_64)，不同浏览器的实现有不同

这里我使用`chrome://tracing`进行探索，

## 人工点击按钮

![img_2.png](img_2.png)

- 从上图中我们可以看到，一次点击事件之后，Blink（Blink是一个渲染引擎，Chrome的Renderer进程中的主线程大部分时间会在Blink和V8两者切换）会调用v8.callFunction进入V8引擎，执行listener1，输出`listener1`。
- 弹栈时发现V8调用栈为空，这时候就会执行V8.RunMicrotasks执行Microtasks队列中的所有Microtask，输出`promise resolved 1`。
- Blink调用v8.callFunction进入V8引擎，执行listener2，输出`listener 2`。
- 弹栈时发现V8调用栈为空，这时候就会执行Microtasks队列中的所有Microtask，输出`promise resolved 2`。

> 注意，chrome://tracing中的`v8.xxx`小写v开头的为Blink的调用，`V8.xxx`大写的V才是真正的V8引擎。

### 详细源码

tracing工具还有一个非常好用的功能，点击下图中的放大镜，就可以直接查看V8的源码。

https://source.chromium.org/chromium/chromium/src/+/master:third_party/blink/renderer/bindings/core/v8/v8_script_runner.cc?q=v8.callFunction&ss=chromium

![img_4.png](img_4.png)

```cpp
// third_party/blink/renderer/bindings/core/v8/v8_script_runner.cc

v8::MaybeLocal<v8::Value> V8ScriptRunner::CallFunction(
    v8::Local<v8::Function> function,
    ExecutionContext* context,
    v8::Local<v8::Value> receiver,
    int argc,
    v8::Local<v8::Value> args[],
    v8::Isolate* isolate) {
  LocalDOMWindow* window = DynamicTo<LocalDOMWindow>(context);
  LocalFrame* frame = window ? window->GetFrame() : nullptr;
  ScopedFrameBlamer frame_blamer(frame);
  TRACE_EVENT0("v8", "v8.callFunction");
  RuntimeCallStatsScopedTracer rcs_scoped_tracer(isolate);
  RUNTIME_CALL_TIMER_SCOPE(isolate, RuntimeCallStats::CounterId::kV8);
 
  v8::MicrotaskQueue* microtask_queue = ToMicrotaskQueue(context);
  int depth = GetMicrotasksScopeDepth(isolate, microtask_queue);
  if (depth >= kMaxRecursionDepth)
    return ThrowStackOverflowExceptionIfNeeded(isolate, microtask_queue);
 
  CHECK(!context->ContextLifecycleObserverSet().IsIteratingOverObservers());
 
  if (ScriptForbiddenScope::IsScriptForbidden()) {
    ThrowScriptForbiddenException(isolate);
    return v8::MaybeLocal<v8::Value>();
  }
 
  DCHECK(!frame || BindingSecurity::ShouldAllowAccessToFrame(
                       ToLocalDOMWindow(function->CreationContext()), frame,
                       BindingSecurity::ErrorReportOption::kDoNotReport));
  v8::Isolate::SafeForTerminationScope safe_for_termination(isolate);
  v8::MicrotasksScope microtasks_scope(isolate, microtask_queue,
                                       v8::MicrotasksScope::kRunMicrotasks);
  if (!depth) {
    TRACE_EVENT_BEGIN1("devtools.timeline", "FunctionCall", "data",
                       [&](perfetto::TracedValue trace_context) {
                         inspector_function_call_event::Data(
                             std::move(trace_context), context, function);
                       });
  }
 
  probe::CallFunction probe(context, function, depth);
  v8::MaybeLocal<v8::Value> result =
      function->Call(isolate->GetCurrentContext(), receiver, argc, args);
  CHECK(!isolate->IsDead());
 
  if (!depth)
    TRACE_EVENT_END0("devtools.timeline", "FunctionCall");
 
  return result;
}
```


```cpp
// v8/src/api/api.cc

MicrotasksScope::MicrotasksScope(Isolate* isolate,
                                 MicrotaskQueue* microtask_queue,
                                 MicrotasksScope::Type type)
    : isolate_(reinterpret_cast<i::Isolate*>(isolate)),
      microtask_queue_(microtask_queue
                           ? static_cast<i::MicrotaskQueue*>(microtask_queue)
                           : isolate_->default_microtask_queue()),
      run_(type == MicrotasksScope::kRunMicrotasks) {
  if (run_) microtask_queue_->IncrementMicrotasksScopeDepth();
#ifdef DEBUG
  if (!run_) microtask_queue_->IncrementDebugMicrotasksScopeDepth();
#endif
}
 
MicrotasksScope::~MicrotasksScope() {
  if (run_) {
    microtask_queue_->DecrementMicrotasksScopeDepth();
    if (MicrotasksPolicy::kScoped == microtask_queue_->microtasks_policy() &&
        !isolate_->has_scheduled_exception()) {
      DCHECK_IMPLIES(isolate_->has_scheduled_exception(),
                     isolate_->scheduled_exception() ==
                         i::ReadOnlyRoots(isolate_).termination_exception());
      microtask_queue_->PerformCheckpoint(reinterpret_cast<Isolate*>(isolate_));
    }
  }
#ifdef DEBUG
  if (!run_) microtask_queue_->DecrementDebugMicrotasksScopeDepth();
#endif
}
```

```cpp
// v8/src/execution/microtask-queue.cc

void MicrotaskQueue::PerformCheckpoint(v8::Isolate* v8_isolate) {
  if (!IsRunningMicrotasks() && !GetMicrotasksScopeDepth() &&
      !HasMicrotasksSuppressions()) {
    Isolate* isolate = reinterpret_cast<Isolate*>(v8_isolate);
    RunMicrotasks(isolate);
    isolate->ClearKeptObjects();
  }
}

...

int MicrotaskQueue::RunMicrotasks(Isolate* isolate) {
  if (!size()) {
    OnCompleted(isolate);
    return 0;
  }
 
  intptr_t base_count = finished_microtask_count_;
 
  HandleScope handle_scope(isolate);
  MaybeHandle<Object> maybe_exception;
 
  MaybeHandle<Object> maybe_result;
 
  int processed_microtask_count;
  {
    SetIsRunningMicrotasks scope(&is_running_microtasks_);
    v8::Isolate::SuppressMicrotaskExecutionScope suppress(
        reinterpret_cast<v8::Isolate*>(isolate));
    HandleScopeImplementer::EnteredContextRewindScope rewind_scope(
        isolate->handle_scope_implementer());
    TRACE_EVENT_BEGIN0("v8.execute", "RunMicrotasks");
    {
      TRACE_EVENT_CALL_STATS_SCOPED(isolate, "v8", "V8.RunMicrotasks");
      maybe_result = Execution::TryRunMicrotasks(isolate, this,
                                                 &maybe_exception);
      processed_microtask_count =
          static_cast<int>(finished_microtask_count_ - base_count);
    }
    TRACE_EVENT_END1("v8.execute", "RunMicrotasks", "microtask_count",
                     processed_microtask_count);
  }
 
  // If execution is terminating, clean up and propagate that to TryCatch scope.
  if (maybe_result.is_null() && maybe_exception.is_null()) {
    delete[] ring_buffer_;
    ring_buffer_ = nullptr;
    capacity_ = 0;
    size_ = 0;
    start_ = 0;
    DCHECK(isolate->has_scheduled_exception());
    isolate->SetTerminationOnExternalTryCatch();
    OnCompleted(isolate);
    return -1;
  }
  DCHECK_EQ(0, size());
  OnCompleted(isolate);
 
  return processed_microtask_count;
}
```

## JS触发点击事件

![img_3.png](img_3.png)


### 详细源码

```cpp
// third_party/blink/renderer/bindings/core/v8/v8_script_runner.cc

v8::MaybeLocal<v8::Value> V8ScriptRunner::RunCompiledScript(
    v8::Isolate* isolate,
    v8::Local<v8::Script> script,
    ExecutionContext* context) {
  DCHECK(!script.IsEmpty());
  LocalDOMWindow* window = DynamicTo<LocalDOMWindow>(context);
  ScopedFrameBlamer frame_blamer(window ? window->GetFrame() : nullptr);
 
  v8::Local<v8::Value> script_name =
      script->GetUnboundScript()->GetScriptName();
  TRACE_EVENT1("v8", "v8.run", "fileName",
               TRACE_STR_COPY(*v8::String::Utf8Value(isolate, script_name)));
  RuntimeCallStatsScopedTracer rcs_scoped_tracer(isolate);
  RUNTIME_CALL_TIMER_SCOPE(isolate, RuntimeCallStats::CounterId::kV8);
 
  v8::MicrotaskQueue* microtask_queue = ToMicrotaskQueue(context);
  if (GetMicrotasksScopeDepth(isolate, microtask_queue) > kMaxRecursionDepth)
    return ThrowStackOverflowExceptionIfNeeded(isolate, microtask_queue);
 
  CHECK(!context->ContextLifecycleObserverSet().IsIteratingOverObservers());
 
  // Run the script and keep track of the current recursion depth.
  v8::MaybeLocal<v8::Value> result;
  {
    if (ScriptForbiddenScope::IsScriptForbidden()) {
      ThrowScriptForbiddenException(isolate);
      return v8::MaybeLocal<v8::Value>();
    }
 
    v8::Isolate::SafeForTerminationScope safe_for_termination(isolate);
    v8::MicrotasksScope microtasks_scope(isolate, microtask_queue,
                                         v8::MicrotasksScope::kRunMicrotasks);
    v8::Local<v8::String> script_url;
    if (!script_name->ToString(isolate->GetCurrentContext())
             .ToLocal(&script_url))
      return result;
 
    // ToCoreString here should be zero copy due to externalized string
    // unpacked.
    probe::ExecuteScript probe(context, ToCoreString(script_url),
                               script->GetUnboundScript()->GetId());
    result = script->Run(isolate->GetCurrentContext());
  }
 
  CHECK(!isolate->IsDead());
  return result;
}

```


> Tips:
> 
> chrome://tracing/ 是一个



# 总结

## what you learn


Event Loop（事件循环）一直是个非常有趣的东西，本文我们探索Microtasks的运行时机，即什么时候会执行Microtasks。

Event Loop（事件循环）是前端工程师经常讨论到的话题，往深挖可以挖出JS如何实现异步、requestAnimation、浏览器渲染机制、Macrotasks、Microtasks等等
