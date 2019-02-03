# -*- coding: utf-8 -*-

from .render import ashes

CONTEXTUAL_ENV = ashes.AshesEnv()


def _register_templates():
    CONTEXTUAL_ENV.register_source('500.html', HTML_500_TMPL)
    CONTEXTUAL_ENV.register_source('404.html', HTML_404_TMPL)


HTML_500_TMPL = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8">
  <meta name="robots" content="NONE,NOARCHIVE">
  <title>{?exc_type}{exc_type}{:else}Exception{/exc_type}{?req.path} at {req.path}{/req.path}</title>
__STYLE_SCRIPT_STUFF__
</head>
<body>
<div id="summary">
  <h1>{?exc_type}{exc_type}{:else}Error{/exc_type}{?req.path} at {req.path}{/req.path}</h1>
  {?exc_value}<pre class="exception_value">{exc_value}</pre>{/exc_value}
  <table class="meta">
    {#req}
    <tr><th>Request Method:</th><td>{.method}</td></tr>
    <tr><th>Request URL:</th><td><span title="{.full_url}">{.abs_path}</span></td></tr>
    {/req}
    <tr><th>Clastic Version:</th><td>{clastic_version_info}</td></tr>
    {?exc_type}
    <tr><th>Exception Type:</th><td>{exc_type}</td></tr>
    {?exc_value}
    <tr><th>Exception Value:</th><td><pre>{exc_value}</pre></td></tr>
    {/exc_value}
    {/exc_type}
    {?last_frame}
    <tr>
      <th>Exception Location:</th>
      <td><a href="#f{last_frame.id}">{last_frame.module_path} in {last_frame.func_name}, line {last_frame.lineno}</a></td>
    </tr>
   {/last_frame}
    <tr><th>Python Executable:</th><td>{python.executable}</td></tr>
    <tr><th>Python Version:</th><td>{python.version}</td></tr>
    <tr><th>Server Time:</th><td title="{server_time_utc} UTC">{server_time}</td></tr>
  </table>
</div>
{?exc_tb.frames}
<div id="traceback">
  <h2>Traceback <span class="commands">{^is_email}<a href="#" onclick="return switchPastebinFriendly(this);">Switch to copy-and-paste view</a></span>{/is_email}</h2>
  <div id="browserTraceback">
    <ul class="traceback">
      {#exc_tb.frames}
        <li id="f{.id}" class="frame {.type} {?is_hidden}hiddenframe{/is_hidden}">
          <code>{.module_path}</code> in <code>{.func_name}</code>:

          {?.line}
            <div class="context" id="c{.id}">
              {^is_email}{?.pre_lines}
              <ol start="{.pre_start_lineno}" class="pre-context" id="pre{.id}">
                {#.pre_lines}<li onclick="toggle('pre{id}', 'post{id}')"><pre>{.line}</pre></li>{/pre_lines}
              </ol>
              {/pre_lines}{/is_email}
              <ol start="{.lineno}" class="context-line"><li onclick="toggle('pre{.id}', 'post{.id}')"><pre>{.line}</pre>{^is_email} <span>...</span>{/is_email}</li></ol>
              {^is_email}{?.post_lines}
              <ol start='{.post_start_lineno}' class="post-context" id="post{id}">
                {#.post_lines}<li onclick="toggle('pre{id}', 'post{id}')"><pre>{.line}</pre></li>{/post_lines}
              </ol>
              {/post_lines}{/is_email}
            </div>
          {/line}

          {?.locals}
            <div class="commands">
                {?is_email}
                    <h2>Local Variables</h2>
                {:else}
                    <a href="#" onclick="return varToggle(this, '{.id}')"><span>&#x25b6;</span> Local variables</a>
                {/is_email}
            </div>
            <table class="vars" id="v{.id}">
              <thead>
                <tr><th>Variable</th><th>Value</th></tr>
              </thead>
              <tbody>
                {@iterate key=locals sort="asc"}
                  <tr><td>{$key}</td><td>{$value}</td></tr>
                {/iterate}
              </tbody>
            </table>
          {/locals}
        </li>
      {/exc_tb.frames}
    </ul>
  </div>
  <form action="http://dpaste.com/" name="pasteform" id="pasteform" method="POST">
{^is_email}
  <div id="pastebinTraceback" class="pastebin">
    <input type="hidden" name="language" value="PythonConsole">
    <input type="hidden" name="title" value="{exc_type}{#req} at {.abs_path}{/req}">
    <input type="hidden" name="source" value="Clastic Dpaste Agent">
    <input type="hidden" name="poster" value="Clastic">
    <textarea name="content" id="traceback_area" cols="140" rows="25">
---  # Clastic Internal Server Error

Exception:
    Type: {exc_type}
    Value: {exc_value}

Request:{#req}
    Method: {.method}
    URL Path: {.abs_path}
    Full URL: {.full_url}
{/req}
Environment:
    Clastic Version: {clastic_version_info}
    Python Version: {python.version}
    Python Executable: {python.executable}
    Server Time: {server_time} ({server_time_utc} UTC)

Traceback: |
  {exc_tb_str}
</textarea>
  <br><br>
  <input type="submit" value="Share this traceback on a public Web site">
  </div>
</form>
</div>
{/is_email}
{/exc_tb.frames}

<div id="requestinfo">
  <h2>Request information</h2>

{?req}
  <h3 id="url-params-h">URL PARAMS</h3>
  {?req.url_params}
    <table class="req">
      <thead>
        <tr>
          <th>Variable</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {@iterate key=req.url_params sort="asc"}
          <tr>
            <td>{$key}</td>
            <td class="code"><pre>{$value|pp}</pre></td>
          </tr>
        {/iterate}
      </tbody>
    </table>
  {:else}
    <p>No query parameters present in URL.</p>
  {/req.url_params}

  <h3 id="form-data-h">FORM DATA</h3>
  {?req.form_data}
    <table class="req">
      <thead>
        <tr>
          <th>Variable</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {@iterate key=req.form_data sort="asc"}
          <tr>
            <td>{$key}</td>
            <td class="code"><pre>{$value|pp}</pre></td>
          </tr>
        {/iterate}
      </tbody>
    </table>
  {:else}
    <p>No form-encoded data submitted.</p>
  {/req.form_data}

  <h3 id="meta-info">HEADERS</h3>
  {?req.headers}
  <table class="req">
    <thead>
      <tr>
        <th>Variable</th>
        <th>Value</th>
      </tr>
    </thead>
    <tbody>
      {@iterate key=req.headers sort="asc"}{?$value}
        <tr>
          <td>{$key}</td>
          <td class="code"><pre>{$value}</pre></td>
        </tr>
      {/$value}{/iterate}
    </tbody>
  </table>
  {:else}
  <p>No request headers present</p>
  {/req.headers}

  <h3 id="cookie-info">COOKIES</h3>
  {?req.cookies}
    <table class="req">
      <thead>
        <tr>
          <th>Variable</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {@iterate key=req.cookies sort="asc"}
          <tr>
            <td>{$key}</td>
            <td class="code"><pre>{$value|pp}</pre></td>
          </tr>
        {/iterate}
      </tbody>
    </table>
  {:else}
    <p>No cookie data</p>
  {/req.cookies}

  <h3 id="files-info">FILES</h3>
  {?request.files}
    <table class="req">
        <thead>
            <tr>
                <th>Variable</th>
                <th>Value</th>
            </tr>
        </thead>
        <tbody>
        {@iterate key=req.files sort="asc"}
          <tr>
            <td>{$key}</td>
            <td class="code"><pre>{$value|pp}</pre></td>
          </tr>
        {/iterate}
        </tbody>
    </table>
  {:else}
    <p>No files uploaded.</p>
  {/request.files}
{:else}
  <p>Request data not supplied</p>
{/req}

{!
  <h3 id="injectables-info">INJECTABLES</h3>
  {?injectables}
    <table class="req">
        <thead>
            <tr>
                <th>Variable</th>
                <th>Value</th>
            </tr>
        </thead>
        <tbody>
        {@iterate key=injectables sort="asc"}
          <tr>
            <td>{$key}</td>
            <td class="code"><pre>{$value}</pre></td>
          </tr>
        {/iterate}
        </tbody>
    </table>
  {:else}
    <p>Injectables not available</p>
  {/injectables}
!}
  <h3 title="{@size key=python.path}{.}{/size} entries">PYTHON PATH</h3>
  <table class="req"><tbody><tr><td>
    <pre>{python.path|pp}</pre>
  </td></tr></tbody></table>
</div>
{^is_email}
  <div id="explanation">
    <p>You're seeing this error because you are in developer/debug mode.
       When served under production settings, Clastic will render a
       standard <code>500 Internal Server Error</code> page.</p>
  </div>
{/is_email}
</body>
</html>
"""


HTML_404_TMPL = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8">
  <title>Page not found{?request} at {request.path}{/request}</title>
  <meta name="robots" content="NONE,NOARCHIVE">
  __STYLE_SCRIPT_STUFF__
</head>
<body>
  <div id="summary">
    <h1>Page not found <small>(404)</small></h1>
    <table class="meta">
      {?request}
      <tr>
        <th>Request Method:</th>
        <td>{request.method}</td>
      </tr>
      <tr>
        <th>Request URL Path:</th>
      <td>{request.path}</td>
      </tr>
      {/request}
    </table>
  </div>
  <div id="info">
      {?routes}
      <p>Clastic tried these URL patterns, in this order:</p>
      <ol>
        {#routes}
          <li>
            <span title="{.regex}">{.pattern}</span> {?.methods}({.methods}){/methods}
          </li>
        {/routes}
      </ol>
      {?request}
      <p>The current URL, <code>{request.path}</code>, didn't match any of these.</p>
      {/request}
    {/routes}
  </div>

  <div id="explanation">
    <p>You're seeing this error because you are in developer/debug mode.
       When served under production settings, Clastic will render a
       standard <code>404 Not Found</code> page.</p>
    </p>
  </div>
</body>
</html>
"""


STYLE_SCRIPT_STUFF = """
  <style type="text/css">
    html * { padding:0; margin:0; }
    body * { padding:10px 20px; }
    body * * { padding:0; }
    body { font:small sans-serif; background: #eee}
    body>div { border-bottom:1px solid #ddd; }
    h1 { font-weight:normal; }
    h1 small { font-size:60%; color:#666; font-weight:normal; }
    h2 { margin-bottom:.8em; }
    h2 span { font-size:80%; color:#666; font-weight:normal; }
    h3 { margin:1em 0 .5em 0; }
    h4 { margin:0 0 .5em 0; font-weight: normal; }
    a { color: #3389c5; }
    code, pre { font-size: 100%; white-space: pre-wrap; }
    table { border:1px solid #ccc; border-collapse: collapse; width:100%; background:white; }
    tbody td, tbody th { vertical-align:top; padding:2px 3px; }
    thead th { padding:1px 6px 1px 3px; background:#fefefe; text-align:left; font-weight:normal; font-size:11px; border:1px solid #ddd; }
    tbody th { width:12em; text-align:right; color:#666; padding-right:.5em; }
    thead th:last-child { width:100% }
    table.vars { margin:5px 0 2px 40px; width:95% }
    table.vars td, table.req td { font-family:monospace; }
    table.req td:first-child { white-space:nowrap; border-right:1px solid #ddd; }
    table td.code { width:100%; }
    table td.code pre { overflow:hidden; }
    table.source th { color:#666; }
    table.source td { font-family:monospace; white-space:pre; border-bottom:1px solid #eee; }
    ul.traceback { list-style-type:none; color: #222; }
    ul.traceback li.frame { padding-bottom:1em; color:#666; }
    ul.traceback li.hiddenframe {display: none;}
    ul.traceback li.user { background-color:#e0e0e0; color:#000 }
    div.context { padding:10px 0; overflow:hidden; }
    div.context ol { padding-left:30px; margin:0 10px; list-style-position: inside; }
    div.context ol li { font-family:monospace; white-space:pre; color:#777; cursor:pointer; }
    div.context ol li pre { display:inline; }
    div.context ol.context-line li { color:#505050; background-color:#dfdfdf; }
    div.context ol.context-line li span { position:absolute; right:32px; }
    .user div.context ol.context-line li { background-color:#bbb; color:#000; }
    .user div.context ol li { color:#666; }
    div.commands { margin-left: 40px; }
    div.commands a { color:#555; text-decoration:none; }
    .user div.commands a { color: black; }
    #summary { background: #ffc; }
    #summary h2 { font-weight: normal; color: #666; }
    #explanation { background:#eee; }
    #template, #template-not-exist { background:#f6f6f6; }
    #template-not-exist ul { margin: 0 0 0 20px; }
    #unicode-hint { background:#eee; }
    #traceback { background:#eee; }
    #requestinfo { background:#f6f6f6; padding-left:140px; }
    #summary table { border:none; background:transparent; }
    #requestinfo h2, #requestinfo h3 { position:relative; margin-left:-120px; }
    #requestinfo h3 { margin-bottom:-1em; }
    .error { background: #ffc; }
    .specific { color:#cc3300; font-weight:bold; }
    h2 span.commands { font-size:.7em;}
    span.commands a:link {color:#5E5694;}
    pre.exception_value { font-family: sans-serif; color: #666; font-size: 1.5em; margin: 10px 0 10px 0; }
    .frame code {font-size:110%}

    /* 404 specific stuff */
    #info { background:#f6f6f6; }
    #info ol { margin: 0.5em 4em; }
    #info ol li { font-family: monospace; }
  </style>
  {^is_email}
  <script type="text/javascript">
  //<!--
    function getElementsByClassName(oElm, strTagName, strClassName){
        // Written by Jonathan Snook, http://www.snook.ca/jon; Add-ons by Robert Nyman, http://www.robertnyman.com
        var arrElements = (strTagName == "*" && document.all)? document.all :
        oElm.getElementsByTagName(strTagName);
        var arrReturnElements = new Array();
        strClassName = strClassName.replace(/\-/g, "\\-");
        var oRegExp = new RegExp("(^|\\s)" + strClassName + "(\\s|$)");
        var oElement;
        for(var i=0; i<arrElements.length; i++){
            oElement = arrElements[i];
            if(oRegExp.test(oElement.className)){
                arrReturnElements.push(oElement);
            }
        }
        return (arrReturnElements)
    }
    function hideAll(elems) {
      for (var e = 0; e < elems.length; e++) {
        elems[e].style.display = 'none';
      }
    }
    window.onload = function() {
      hideAll(getElementsByClassName(document, 'table', 'vars'));
      hideAll(getElementsByClassName(document, 'ol', 'pre-context'));
      hideAll(getElementsByClassName(document, 'ol', 'post-context'));
      hideAll(getElementsByClassName(document, 'div', 'pastebin'));
    }
    function toggle() {
      for (var i = 0; i < arguments.length; i++) {
        var e = document.getElementById(arguments[i]);
        if (e) {
          e.style.display = e.style.display == 'none' ? 'block' : 'none';
        }
      }
      return false;
    }
    function varToggle(link, id) {
      toggle('v' + id);
      var s = link.getElementsByTagName('span')[0];
      var uarr = String.fromCharCode(0x25b6);
      var darr = String.fromCharCode(0x25bc);
      s.innerHTML = s.innerHTML == uarr ? darr : uarr;
      return false;
    }
    function switchPastebinFriendly(link) {
      s1 = "Switch to copy-and-paste view";
      s2 = "Switch back to interactive view";
      link.innerHTML = link.innerHTML == s1 ? s2 : s1;
      toggle('browserTraceback', 'pastebinTraceback');
      return false;
    }
    //-->
  </script>
  {/is_email}
"""

HTML_500_TMPL = HTML_500_TMPL.replace('__STYLE_SCRIPT_STUFF__',
                                      STYLE_SCRIPT_STUFF)
HTML_404_TMPL = HTML_404_TMPL.replace('__STYLE_SCRIPT_STUFF__',
                                      STYLE_SCRIPT_STUFF)

_register_templates()
