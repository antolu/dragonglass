'use strict';

const require$$0$2 = require('obsidian');
const require$$0 = require('node:fs');
const require$$1 = require('node:path');
const require$$0$1 = require('node:buffer');
const require$$1$1 = require('node:crypto');
const require$$2 = require('node:http');

function getDefaultExportFromCjs (x) {
	return x && x.__esModule && Object.prototype.hasOwnProperty.call(x, 'default') ? x['default'] : x;
}

var src;
var hasRequiredSrc;

function requireSrc () {
	if (hasRequiredSrc) return src;
	hasRequiredSrc = 1;
	var __defProp = Object.defineProperty;
	var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
	var __getOwnPropNames = Object.getOwnPropertyNames;
	var __hasOwnProp = Object.prototype.hasOwnProperty;
	var __export = (target, all) => {
	  for (var name in all)
	    __defProp(target, name, { get: all[name], enumerable: true });
	};
	var __copyProps = (to, from, except, desc) => {
	  if (from && typeof from === "object" || typeof from === "function") {
	    for (let key of __getOwnPropNames(from))
	      if (!__hasOwnProp.call(to, key) && key !== except)
	        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
	  }
	  return to;
	};
	var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
	var src_exports = {};
	__export(src_exports, {
	  NoteIndex: () => NoteIndex
	});
	src = __toCommonJS(src_exports);
	class NoteIndex {
	  entries = /* @__PURE__ */ new Map();
	  constructor() {
	  }
	  set(path, entry) {
	    this.entries.set(path, entry);
	  }
	  delete(path) {
	    this.entries.delete(path);
	  }
	  get(path) {
	    return this.entries.get(path);
	  }
	  clear() {
	    this.entries.clear();
	  }
	  getAll() {
	    return Array.from(this.entries.values());
	  }
	  search(queryVector, allowlist, topN = 10) {
	    let candidates = this.getAll();
	    if (allowlist && allowlist.length > 0) {
	      const set = new Set(allowlist);
	      candidates = candidates.filter((e) => set.has(e.path));
	    }
	    const results = candidates.map((entry) => ({
	      path: entry.path,
	      score: this.cosineSimilarity(queryVector, entry.vector)
	    }));
	    return results.sort((a, b) => b.score - a.score).slice(0, topN);
	  }
	  cosineSimilarity(v1, v2) {
	    let dotProduct = 0;
	    let mag1 = 0;
	    let mag2 = 0;
	    for (let i = 0; i < v1.length; i++) {
	      dotProduct += v1[i] * v2[i];
	      mag1 += v1[i] * v1[i];
	      mag2 += v2[i] * v2[i];
	    }
	    mag1 = Math.sqrt(mag1);
	    mag2 = Math.sqrt(mag2);
	    if (mag1 === 0 || mag2 === 0)
	      return 0;
	    return dotProduct / (mag1 * mag2);
	  }
	  serialize() {
	    return JSON.stringify(Array.from(this.entries.values()));
	  }
	  deserialize(json) {
	    try {
	      const data = JSON.parse(json);
	      this.entries.clear();
	      for (const entry of data) {
	        this.entries.set(entry.path, entry);
	      }
	    } catch (e) {
	      console.error("Failed to deserialize index", e);
	    }
	  }
	  sizeInBytes() {
	    return new TextEncoder().encode(this.serialize()).length;
	  }
	}
	return src;
}

var dist = {};

var browser = {};

/* eslint-disable no-prototype-builtins */
var g =
  (typeof globalThis !== 'undefined' && globalThis) ||
  (typeof self !== 'undefined' && self) ||
  // eslint-disable-next-line no-undef
  (typeof global !== 'undefined' && global) ||
  {};

var support = {
  searchParams: 'URLSearchParams' in g,
  iterable: 'Symbol' in g && 'iterator' in Symbol,
  blob:
    'FileReader' in g &&
    'Blob' in g &&
    (function() {
      try {
        new Blob();
        return true
      } catch (e) {
        return false
      }
    })(),
  formData: 'FormData' in g,
  arrayBuffer: 'ArrayBuffer' in g
};

function isDataView(obj) {
  return obj && DataView.prototype.isPrototypeOf(obj)
}

if (support.arrayBuffer) {
  var viewClasses = [
    '[object Int8Array]',
    '[object Uint8Array]',
    '[object Uint8ClampedArray]',
    '[object Int16Array]',
    '[object Uint16Array]',
    '[object Int32Array]',
    '[object Uint32Array]',
    '[object Float32Array]',
    '[object Float64Array]'
  ];

  var isArrayBufferView =
    ArrayBuffer.isView ||
    function(obj) {
      return obj && viewClasses.indexOf(Object.prototype.toString.call(obj)) > -1
    };
}

function normalizeName(name) {
  if (typeof name !== 'string') {
    name = String(name);
  }
  if (/[^a-z0-9\-#$%&'*+.^_`|~!]/i.test(name) || name === '') {
    throw new TypeError('Invalid character in header field name: "' + name + '"')
  }
  return name.toLowerCase()
}

function normalizeValue(value) {
  if (typeof value !== 'string') {
    value = String(value);
  }
  return value
}

// Build a destructive iterator for the value list
function iteratorFor(items) {
  var iterator = {
    next: function() {
      var value = items.shift();
      return {done: value === undefined, value: value}
    }
  };

  if (support.iterable) {
    iterator[Symbol.iterator] = function() {
      return iterator
    };
  }

  return iterator
}

function Headers$1(headers) {
  this.map = {};

  if (headers instanceof Headers$1) {
    headers.forEach(function(value, name) {
      this.append(name, value);
    }, this);
  } else if (Array.isArray(headers)) {
    headers.forEach(function(header) {
      if (header.length != 2) {
        throw new TypeError('Headers constructor: expected name/value pair to be length 2, found' + header.length)
      }
      this.append(header[0], header[1]);
    }, this);
  } else if (headers) {
    Object.getOwnPropertyNames(headers).forEach(function(name) {
      this.append(name, headers[name]);
    }, this);
  }
}

Headers$1.prototype.append = function(name, value) {
  name = normalizeName(name);
  value = normalizeValue(value);
  var oldValue = this.map[name];
  this.map[name] = oldValue ? oldValue + ', ' + value : value;
};

Headers$1.prototype['delete'] = function(name) {
  delete this.map[normalizeName(name)];
};

Headers$1.prototype.get = function(name) {
  name = normalizeName(name);
  return this.has(name) ? this.map[name] : null
};

Headers$1.prototype.has = function(name) {
  return this.map.hasOwnProperty(normalizeName(name))
};

Headers$1.prototype.set = function(name, value) {
  this.map[normalizeName(name)] = normalizeValue(value);
};

Headers$1.prototype.forEach = function(callback, thisArg) {
  for (var name in this.map) {
    if (this.map.hasOwnProperty(name)) {
      callback.call(thisArg, this.map[name], name, this);
    }
  }
};

Headers$1.prototype.keys = function() {
  var items = [];
  this.forEach(function(value, name) {
    items.push(name);
  });
  return iteratorFor(items)
};

Headers$1.prototype.values = function() {
  var items = [];
  this.forEach(function(value) {
    items.push(value);
  });
  return iteratorFor(items)
};

Headers$1.prototype.entries = function() {
  var items = [];
  this.forEach(function(value, name) {
    items.push([name, value]);
  });
  return iteratorFor(items)
};

if (support.iterable) {
  Headers$1.prototype[Symbol.iterator] = Headers$1.prototype.entries;
}

function consumed(body) {
  if (body._noBody) return
  if (body.bodyUsed) {
    return Promise.reject(new TypeError('Already read'))
  }
  body.bodyUsed = true;
}

function fileReaderReady(reader) {
  return new Promise(function(resolve, reject) {
    reader.onload = function() {
      resolve(reader.result);
    };
    reader.onerror = function() {
      reject(reader.error);
    };
  })
}

function readBlobAsArrayBuffer(blob) {
  var reader = new FileReader();
  var promise = fileReaderReady(reader);
  reader.readAsArrayBuffer(blob);
  return promise
}

function readBlobAsText(blob) {
  var reader = new FileReader();
  var promise = fileReaderReady(reader);
  var match = /charset=([A-Za-z0-9_-]+)/.exec(blob.type);
  var encoding = match ? match[1] : 'utf-8';
  reader.readAsText(blob, encoding);
  return promise
}

function readArrayBufferAsText(buf) {
  var view = new Uint8Array(buf);
  var chars = new Array(view.length);

  for (var i = 0; i < view.length; i++) {
    chars[i] = String.fromCharCode(view[i]);
  }
  return chars.join('')
}

function bufferClone(buf) {
  if (buf.slice) {
    return buf.slice(0)
  } else {
    var view = new Uint8Array(buf.byteLength);
    view.set(new Uint8Array(buf));
    return view.buffer
  }
}

function Body() {
  this.bodyUsed = false;

  this._initBody = function(body) {
    /*
      fetch-mock wraps the Response object in an ES6 Proxy to
      provide useful test harness features such as flush. However, on
      ES5 browsers without fetch or Proxy support pollyfills must be used;
      the proxy-pollyfill is unable to proxy an attribute unless it exists
      on the object before the Proxy is created. This change ensures
      Response.bodyUsed exists on the instance, while maintaining the
      semantic of setting Request.bodyUsed in the constructor before
      _initBody is called.
    */
    // eslint-disable-next-line no-self-assign
    this.bodyUsed = this.bodyUsed;
    this._bodyInit = body;
    if (!body) {
      this._noBody = true;
      this._bodyText = '';
    } else if (typeof body === 'string') {
      this._bodyText = body;
    } else if (support.blob && Blob.prototype.isPrototypeOf(body)) {
      this._bodyBlob = body;
    } else if (support.formData && FormData.prototype.isPrototypeOf(body)) {
      this._bodyFormData = body;
    } else if (support.searchParams && URLSearchParams.prototype.isPrototypeOf(body)) {
      this._bodyText = body.toString();
    } else if (support.arrayBuffer && support.blob && isDataView(body)) {
      this._bodyArrayBuffer = bufferClone(body.buffer);
      // IE 10-11 can't handle a DataView body.
      this._bodyInit = new Blob([this._bodyArrayBuffer]);
    } else if (support.arrayBuffer && (ArrayBuffer.prototype.isPrototypeOf(body) || isArrayBufferView(body))) {
      this._bodyArrayBuffer = bufferClone(body);
    } else {
      this._bodyText = body = Object.prototype.toString.call(body);
    }

    if (!this.headers.get('content-type')) {
      if (typeof body === 'string') {
        this.headers.set('content-type', 'text/plain;charset=UTF-8');
      } else if (this._bodyBlob && this._bodyBlob.type) {
        this.headers.set('content-type', this._bodyBlob.type);
      } else if (support.searchParams && URLSearchParams.prototype.isPrototypeOf(body)) {
        this.headers.set('content-type', 'application/x-www-form-urlencoded;charset=UTF-8');
      }
    }
  };

  if (support.blob) {
    this.blob = function() {
      var rejected = consumed(this);
      if (rejected) {
        return rejected
      }

      if (this._bodyBlob) {
        return Promise.resolve(this._bodyBlob)
      } else if (this._bodyArrayBuffer) {
        return Promise.resolve(new Blob([this._bodyArrayBuffer]))
      } else if (this._bodyFormData) {
        throw new Error('could not read FormData body as blob')
      } else {
        return Promise.resolve(new Blob([this._bodyText]))
      }
    };
  }

  this.arrayBuffer = function() {
    if (this._bodyArrayBuffer) {
      var isConsumed = consumed(this);
      if (isConsumed) {
        return isConsumed
      } else if (ArrayBuffer.isView(this._bodyArrayBuffer)) {
        return Promise.resolve(
          this._bodyArrayBuffer.buffer.slice(
            this._bodyArrayBuffer.byteOffset,
            this._bodyArrayBuffer.byteOffset + this._bodyArrayBuffer.byteLength
          )
        )
      } else {
        return Promise.resolve(this._bodyArrayBuffer)
      }
    } else if (support.blob) {
      return this.blob().then(readBlobAsArrayBuffer)
    } else {
      throw new Error('could not read as ArrayBuffer')
    }
  };

  this.text = function() {
    var rejected = consumed(this);
    if (rejected) {
      return rejected
    }

    if (this._bodyBlob) {
      return readBlobAsText(this._bodyBlob)
    } else if (this._bodyArrayBuffer) {
      return Promise.resolve(readArrayBufferAsText(this._bodyArrayBuffer))
    } else if (this._bodyFormData) {
      throw new Error('could not read FormData body as text')
    } else {
      return Promise.resolve(this._bodyText)
    }
  };

  if (support.formData) {
    this.formData = function() {
      return this.text().then(decode)
    };
  }

  this.json = function() {
    return this.text().then(JSON.parse)
  };

  return this
}

// HTTP methods whose capitalization should be normalized
var methods = ['CONNECT', 'DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT', 'TRACE'];

function normalizeMethod(method) {
  var upcased = method.toUpperCase();
  return methods.indexOf(upcased) > -1 ? upcased : method
}

function Request(input, options) {
  if (!(this instanceof Request)) {
    throw new TypeError('Please use the "new" operator, this DOM object constructor cannot be called as a function.')
  }

  options = options || {};
  var body = options.body;

  if (input instanceof Request) {
    if (input.bodyUsed) {
      throw new TypeError('Already read')
    }
    this.url = input.url;
    this.credentials = input.credentials;
    if (!options.headers) {
      this.headers = new Headers$1(input.headers);
    }
    this.method = input.method;
    this.mode = input.mode;
    this.signal = input.signal;
    if (!body && input._bodyInit != null) {
      body = input._bodyInit;
      input.bodyUsed = true;
    }
  } else {
    this.url = String(input);
  }

  this.credentials = options.credentials || this.credentials || 'same-origin';
  if (options.headers || !this.headers) {
    this.headers = new Headers$1(options.headers);
  }
  this.method = normalizeMethod(options.method || this.method || 'GET');
  this.mode = options.mode || this.mode || null;
  this.signal = options.signal || this.signal || (function () {
    if ('AbortController' in g) {
      var ctrl = new AbortController();
      return ctrl.signal;
    }
  }());
  this.referrer = null;

  if ((this.method === 'GET' || this.method === 'HEAD') && body) {
    throw new TypeError('Body not allowed for GET or HEAD requests')
  }
  this._initBody(body);

  if (this.method === 'GET' || this.method === 'HEAD') {
    if (options.cache === 'no-store' || options.cache === 'no-cache') {
      // Search for a '_' parameter in the query string
      var reParamSearch = /([?&])_=[^&]*/;
      if (reParamSearch.test(this.url)) {
        // If it already exists then set the value with the current time
        this.url = this.url.replace(reParamSearch, '$1_=' + new Date().getTime());
      } else {
        // Otherwise add a new '_' parameter to the end with the current time
        var reQueryString = /\?/;
        this.url += (reQueryString.test(this.url) ? '&' : '?') + '_=' + new Date().getTime();
      }
    }
  }
}

Request.prototype.clone = function() {
  return new Request(this, {body: this._bodyInit})
};

function decode(body) {
  var form = new FormData();
  body
    .trim()
    .split('&')
    .forEach(function(bytes) {
      if (bytes) {
        var split = bytes.split('=');
        var name = split.shift().replace(/\+/g, ' ');
        var value = split.join('=').replace(/\+/g, ' ');
        form.append(decodeURIComponent(name), decodeURIComponent(value));
      }
    });
  return form
}

function parseHeaders(rawHeaders) {
  var headers = new Headers$1();
  // Replace instances of \r\n and \n followed by at least one space or horizontal tab with a space
  // https://tools.ietf.org/html/rfc7230#section-3.2
  var preProcessedHeaders = rawHeaders.replace(/\r?\n[\t ]+/g, ' ');
  // Avoiding split via regex to work around a common IE11 bug with the core-js 3.6.0 regex polyfill
  // https://github.com/github/fetch/issues/748
  // https://github.com/zloirock/core-js/issues/751
  preProcessedHeaders
    .split('\r')
    .map(function(header) {
      return header.indexOf('\n') === 0 ? header.substr(1, header.length) : header
    })
    .forEach(function(line) {
      var parts = line.split(':');
      var key = parts.shift().trim();
      if (key) {
        var value = parts.join(':').trim();
        try {
          headers.append(key, value);
        } catch (error) {
          console.warn('Response ' + error.message);
        }
      }
    });
  return headers
}

Body.call(Request.prototype);

function Response(bodyInit, options) {
  if (!(this instanceof Response)) {
    throw new TypeError('Please use the "new" operator, this DOM object constructor cannot be called as a function.')
  }
  if (!options) {
    options = {};
  }

  this.type = 'default';
  this.status = options.status === undefined ? 200 : options.status;
  if (this.status < 200 || this.status > 599) {
    throw new RangeError("Failed to construct 'Response': The status provided (0) is outside the range [200, 599].")
  }
  this.ok = this.status >= 200 && this.status < 300;
  this.statusText = options.statusText === undefined ? '' : '' + options.statusText;
  this.headers = new Headers$1(options.headers);
  this.url = options.url || '';
  this._initBody(bodyInit);
}

Body.call(Response.prototype);

Response.prototype.clone = function() {
  return new Response(this._bodyInit, {
    status: this.status,
    statusText: this.statusText,
    headers: new Headers$1(this.headers),
    url: this.url
  })
};

Response.error = function() {
  var response = new Response(null, {status: 200, statusText: ''});
  response.ok = false;
  response.status = 0;
  response.type = 'error';
  return response
};

var redirectStatuses = [301, 302, 303, 307, 308];

Response.redirect = function(url, status) {
  if (redirectStatuses.indexOf(status) === -1) {
    throw new RangeError('Invalid status code')
  }

  return new Response(null, {status: status, headers: {location: url}})
};

var DOMException = g.DOMException;
try {
  new DOMException();
} catch (err) {
  DOMException = function(message, name) {
    this.message = message;
    this.name = name;
    var error = Error(message);
    this.stack = error.stack;
  };
  DOMException.prototype = Object.create(Error.prototype);
  DOMException.prototype.constructor = DOMException;
}

function fetch$1(input, init) {
  return new Promise(function(resolve, reject) {
    var request = new Request(input, init);

    if (request.signal && request.signal.aborted) {
      return reject(new DOMException('Aborted', 'AbortError'))
    }

    var xhr = new XMLHttpRequest();

    function abortXhr() {
      xhr.abort();
    }

    xhr.onload = function() {
      var options = {
        statusText: xhr.statusText,
        headers: parseHeaders(xhr.getAllResponseHeaders() || '')
      };
      // This check if specifically for when a user fetches a file locally from the file system
      // Only if the status is out of a normal range
      if (request.url.indexOf('file://') === 0 && (xhr.status < 200 || xhr.status > 599)) {
        options.status = 200;
      } else {
        options.status = xhr.status;
      }
      options.url = 'responseURL' in xhr ? xhr.responseURL : options.headers.get('X-Request-URL');
      var body = 'response' in xhr ? xhr.response : xhr.responseText;
      setTimeout(function() {
        resolve(new Response(body, options));
      }, 0);
    };

    xhr.onerror = function() {
      setTimeout(function() {
        reject(new TypeError('Network request failed'));
      }, 0);
    };

    xhr.ontimeout = function() {
      setTimeout(function() {
        reject(new TypeError('Network request timed out'));
      }, 0);
    };

    xhr.onabort = function() {
      setTimeout(function() {
        reject(new DOMException('Aborted', 'AbortError'));
      }, 0);
    };

    function fixUrl(url) {
      try {
        return url === '' && g.location.href ? g.location.href : url
      } catch (e) {
        return url
      }
    }

    xhr.open(request.method, fixUrl(request.url), true);

    if (request.credentials === 'include') {
      xhr.withCredentials = true;
    } else if (request.credentials === 'omit') {
      xhr.withCredentials = false;
    }

    if ('responseType' in xhr) {
      if (support.blob) {
        xhr.responseType = 'blob';
      } else if (
        support.arrayBuffer
      ) {
        xhr.responseType = 'arraybuffer';
      }
    }

    if (init && typeof init.headers === 'object' && !(init.headers instanceof Headers$1 || (g.Headers && init.headers instanceof g.Headers))) {
      var names = [];
      Object.getOwnPropertyNames(init.headers).forEach(function(name) {
        names.push(normalizeName(name));
        xhr.setRequestHeader(name, normalizeValue(init.headers[name]));
      });
      request.headers.forEach(function(value, name) {
        if (names.indexOf(name) === -1) {
          xhr.setRequestHeader(name, value);
        }
      });
    } else {
      request.headers.forEach(function(value, name) {
        xhr.setRequestHeader(name, value);
      });
    }

    if (request.signal) {
      request.signal.addEventListener('abort', abortXhr);

      xhr.onreadystatechange = function() {
        // DONE (success or failure)
        if (xhr.readyState === 4) {
          request.signal.removeEventListener('abort', abortXhr);
        }
      };
    }

    xhr.send(typeof request._bodyInit === 'undefined' ? null : request._bodyInit);
  })
}

fetch$1.polyfill = true;

if (!g.fetch) {
  g.fetch = fetch$1;
  g.Headers = Headers$1;
  g.Request = Request;
  g.Response = Response;
}

var hasRequiredBrowser;

function requireBrowser () {
	if (hasRequiredBrowser) return browser;
	hasRequiredBrowser = 1;

	Object.defineProperty(browser, '__esModule', { value: true });



	const defaultPort = "11434";
	const defaultHost = `http://127.0.0.1:${defaultPort}`;

	const version = "0.6.3";

	var __defProp$1 = Object.defineProperty;
	var __defNormalProp$1 = (obj, key, value) => key in obj ? __defProp$1(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
	var __publicField$1 = (obj, key, value) => {
	  __defNormalProp$1(obj, typeof key !== "symbol" ? key + "" : key, value);
	  return value;
	};
	class ResponseError extends Error {
	  constructor(error, status_code) {
	    super(error);
	    this.error = error;
	    this.status_code = status_code;
	    this.name = "ResponseError";
	    if (Error.captureStackTrace) {
	      Error.captureStackTrace(this, ResponseError);
	    }
	  }
	}
	class AbortableAsyncIterator {
	  constructor(abortController, itr, doneCallback) {
	    __publicField$1(this, "abortController");
	    __publicField$1(this, "itr");
	    __publicField$1(this, "doneCallback");
	    this.abortController = abortController;
	    this.itr = itr;
	    this.doneCallback = doneCallback;
	  }
	  abort() {
	    this.abortController.abort();
	  }
	  async *[Symbol.asyncIterator]() {
	    for await (const message of this.itr) {
	      if ("error" in message) {
	        throw new Error(message.error);
	      }
	      yield message;
	      if (message.done || message.status === "success") {
	        this.doneCallback();
	        return;
	      }
	    }
	    throw new Error("Did not receive done or success response in stream.");
	  }
	}
	const checkOk = async (response) => {
	  if (response.ok) {
	    return;
	  }
	  let message = `Error ${response.status}: ${response.statusText}`;
	  let errorData = null;
	  if (response.headers.get("content-type")?.includes("application/json")) {
	    try {
	      errorData = await response.json();
	      message = errorData.error || message;
	    } catch (error) {
	      console.log("Failed to parse error response as JSON");
	    }
	  } else {
	    try {
	      console.log("Getting text from response");
	      const textResponse = await response.text();
	      message = textResponse || message;
	    } catch (error) {
	      console.log("Failed to get text from error response");
	    }
	  }
	  throw new ResponseError(message, response.status);
	};
	function getPlatform() {
	  if (typeof window !== "undefined" && window.navigator) {
	    const nav = navigator;
	    if ("userAgentData" in nav && nav.userAgentData?.platform) {
	      return `${nav.userAgentData.platform.toLowerCase()} Browser/${navigator.userAgent};`;
	    }
	    if (navigator.platform) {
	      return `${navigator.platform.toLowerCase()} Browser/${navigator.userAgent};`;
	    }
	    return `unknown Browser/${navigator.userAgent};`;
	  } else if (typeof process !== "undefined") {
	    return `${process.arch} ${process.platform} Node.js/${process.version}`;
	  }
	  return "";
	}
	function normalizeHeaders(headers) {
	  if (headers instanceof Headers) {
	    const obj = {};
	    headers.forEach((value, key) => {
	      obj[key] = value;
	    });
	    return obj;
	  } else if (Array.isArray(headers)) {
	    return Object.fromEntries(headers);
	  } else {
	    return headers || {};
	  }
	}
	const readEnvVar = (obj, key) => {
	  return obj[key];
	};
	const fetchWithHeaders = async (fetch, url, options = {}) => {
	  const defaultHeaders = {
	    "Content-Type": "application/json",
	    Accept: "application/json",
	    "User-Agent": `ollama-js/${version} (${getPlatform()})`
	  };
	  options.headers = normalizeHeaders(options.headers);
	  try {
	    const parsed = new URL(url);
	    if (parsed.protocol === "https:" && parsed.hostname === "ollama.com") {
	      const apiKey = typeof process === "object" && process !== null && typeof process.env === "object" && process.env !== null ? readEnvVar(process.env, "OLLAMA_API_KEY") : void 0;
	      const authorization = options.headers["authorization"] || options.headers["Authorization"];
	      if (!authorization && apiKey) {
	        options.headers["Authorization"] = `Bearer ${apiKey}`;
	      }
	    }
	  } catch (error) {
	    console.error("error parsing url", error);
	  }
	  const customHeaders = Object.fromEntries(
	    Object.entries(options.headers).filter(
	      ([key]) => !Object.keys(defaultHeaders).some(
	        (defaultKey) => defaultKey.toLowerCase() === key.toLowerCase()
	      )
	    )
	  );
	  options.headers = {
	    ...defaultHeaders,
	    ...customHeaders
	  };
	  return fetch(url, options);
	};
	const get = async (fetch, host, options) => {
	  const response = await fetchWithHeaders(fetch, host, {
	    headers: options?.headers
	  });
	  await checkOk(response);
	  return response;
	};
	const post = async (fetch, host, data, options) => {
	  const isRecord = (input) => {
	    return input !== null && typeof input === "object" && !Array.isArray(input);
	  };
	  const formattedData = isRecord(data) ? JSON.stringify(data) : data;
	  const response = await fetchWithHeaders(fetch, host, {
	    method: "POST",
	    body: formattedData,
	    signal: options?.signal,
	    headers: options?.headers
	  });
	  await checkOk(response);
	  return response;
	};
	const del = async (fetch, host, data, options) => {
	  const response = await fetchWithHeaders(fetch, host, {
	    method: "DELETE",
	    body: JSON.stringify(data),
	    headers: options?.headers
	  });
	  await checkOk(response);
	  return response;
	};
	const parseJSON = async function* (itr) {
	  const decoder = new TextDecoder("utf-8");
	  let buffer = "";
	  const reader = itr.getReader();
	  while (true) {
	    const { done, value: chunk } = await reader.read();
	    if (done) {
	      break;
	    }
	    buffer += decoder.decode(chunk, { stream: true });
	    const parts = buffer.split("\n");
	    buffer = parts.pop() ?? "";
	    for (const part of parts) {
	      try {
	        yield JSON.parse(part);
	      } catch (error) {
	        console.warn("invalid json: ", part);
	      }
	    }
	  }
	  buffer += decoder.decode();
	  for (const part of buffer.split("\n").filter((p) => p !== "")) {
	    try {
	      yield JSON.parse(part);
	    } catch (error) {
	      console.warn("invalid json: ", part);
	    }
	  }
	};
	const formatHost = (host) => {
	  if (!host) {
	    return defaultHost;
	  }
	  let isExplicitProtocol = host.includes("://");
	  if (host.startsWith(":")) {
	    host = `http://127.0.0.1${host}`;
	    isExplicitProtocol = true;
	  }
	  if (!isExplicitProtocol) {
	    host = `http://${host}`;
	  }
	  const url = new URL(host);
	  let port = url.port;
	  if (!port) {
	    if (!isExplicitProtocol) {
	      port = defaultPort;
	    } else {
	      port = url.protocol === "https:" ? "443" : "80";
	    }
	  }
	  let auth = "";
	  if (url.username) {
	    auth = url.username;
	    if (url.password) {
	      auth += `:${url.password}`;
	    }
	    auth += "@";
	  }
	  let formattedHost = `${url.protocol}//${auth}${url.hostname}:${port}${url.pathname}`;
	  if (formattedHost.endsWith("/")) {
	    formattedHost = formattedHost.slice(0, -1);
	  }
	  return formattedHost;
	};

	var __defProp = Object.defineProperty;
	var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
	var __publicField = (obj, key, value) => {
	  __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);
	  return value;
	};
	let Ollama$1 = class Ollama {
	  constructor(config) {
	    __publicField(this, "config");
	    __publicField(this, "fetch");
	    __publicField(this, "ongoingStreamedRequests", []);
	    this.config = {
	      host: "",
	      headers: config?.headers
	    };
	    if (!config?.proxy) {
	      this.config.host = formatHost(config?.host ?? defaultHost);
	    }
	    this.fetch = config?.fetch ?? fetch;
	  }
	  // Abort any ongoing streamed requests to Ollama
	  abort() {
	    for (const request of this.ongoingStreamedRequests) {
	      request.abort();
	    }
	    this.ongoingStreamedRequests.length = 0;
	  }
	  /**
	   * Processes a request to the Ollama server. If the request is streamable, it will return a
	   * AbortableAsyncIterator that yields the response messages. Otherwise, it will return the response
	   * object.
	   * @param endpoint {string} - The endpoint to send the request to.
	   * @param request {object} - The request object to send to the endpoint.
	   * @protected {T | AbortableAsyncIterator<T>} - The response object or a AbortableAsyncIterator that yields
	   * response messages.
	   * @throws {Error} - If the response body is missing or if the response is an error.
	   * @returns {Promise<T | AbortableAsyncIterator<T>>} - The response object or a AbortableAsyncIterator that yields the streamed response.
	   */
	  async processStreamableRequest(endpoint, request) {
	    request.stream = request.stream ?? false;
	    const host = `${this.config.host}/api/${endpoint}`;
	    if (request.stream) {
	      const abortController = new AbortController();
	      const response2 = await post(this.fetch, host, request, {
	        signal: abortController.signal,
	        headers: this.config.headers
	      });
	      if (!response2.body) {
	        throw new Error("Missing body");
	      }
	      const itr = parseJSON(response2.body);
	      const abortableAsyncIterator = new AbortableAsyncIterator(
	        abortController,
	        itr,
	        () => {
	          const i = this.ongoingStreamedRequests.indexOf(abortableAsyncIterator);
	          if (i > -1) {
	            this.ongoingStreamedRequests.splice(i, 1);
	          }
	        }
	      );
	      this.ongoingStreamedRequests.push(abortableAsyncIterator);
	      return abortableAsyncIterator;
	    }
	    const response = await post(this.fetch, host, request, {
	      headers: this.config.headers
	    });
	    return await response.json();
	  }
	  /**
	   * Encodes an image to base64 if it is a Uint8Array.
	   * @param image {Uint8Array | string} - The image to encode.
	   * @returns {Promise<string>} - The base64 encoded image.
	   */
	  async encodeImage(image) {
	    if (typeof image !== "string") {
	      const uint8Array = new Uint8Array(image);
	      let byteString = "";
	      const len = uint8Array.byteLength;
	      for (let i = 0; i < len; i++) {
	        byteString += String.fromCharCode(uint8Array[i]);
	      }
	      return btoa(byteString);
	    }
	    return image;
	  }
	  /**
	   * Generates a response from a text prompt.
	   * @param request {GenerateRequest} - The request object.
	   * @returns {Promise<GenerateResponse | AbortableAsyncIterator<GenerateResponse>>} - The response object or
	   * an AbortableAsyncIterator that yields response messages.
	   */
	  async generate(request) {
	    if (request.images) {
	      request.images = await Promise.all(request.images.map(this.encodeImage.bind(this)));
	    }
	    return this.processStreamableRequest("generate", request);
	  }
	  /**
	   * Chats with the model. The request object can contain messages with images that are either
	   * Uint8Arrays or base64 encoded strings. The images will be base64 encoded before sending the
	   * request.
	   * @param request {ChatRequest} - The request object.
	   * @returns {Promise<ChatResponse | AbortableAsyncIterator<ChatResponse>>} - The response object or an
	   * AbortableAsyncIterator that yields response messages.
	   */
	  async chat(request) {
	    if (request.messages) {
	      for (const message of request.messages) {
	        if (message.images) {
	          message.images = await Promise.all(
	            message.images.map(this.encodeImage.bind(this))
	          );
	        }
	      }
	    }
	    return this.processStreamableRequest("chat", request);
	  }
	  /**
	   * Creates a new model from a stream of data.
	   * @param request {CreateRequest} - The request object.
	   * @returns {Promise<ProgressResponse | AbortableAsyncIterator<ProgressResponse>>} - The response object or a stream of progress responses.
	   */
	  async create(request) {
	    return this.processStreamableRequest("create", {
	      ...request
	    });
	  }
	  /**
	   * Pulls a model from the Ollama registry. The request object can contain a stream flag to indicate if the
	   * response should be streamed.
	   * @param request {PullRequest} - The request object.
	   * @returns {Promise<ProgressResponse | AbortableAsyncIterator<ProgressResponse>>} - The response object or
	   * an AbortableAsyncIterator that yields response messages.
	   */
	  async pull(request) {
	    return this.processStreamableRequest("pull", {
	      name: request.model,
	      stream: request.stream,
	      insecure: request.insecure
	    });
	  }
	  /**
	   * Pushes a model to the Ollama registry. The request object can contain a stream flag to indicate if the
	   * response should be streamed.
	   * @param request {PushRequest} - The request object.
	   * @returns {Promise<ProgressResponse | AbortableAsyncIterator<ProgressResponse>>} - The response object or
	   * an AbortableAsyncIterator that yields response messages.
	   */
	  async push(request) {
	    return this.processStreamableRequest("push", {
	      name: request.model,
	      stream: request.stream,
	      insecure: request.insecure
	    });
	  }
	  /**
	   * Deletes a model from the server. The request object should contain the name of the model to
	   * delete.
	   * @param request {DeleteRequest} - The request object.
	   * @returns {Promise<StatusResponse>} - The response object.
	   */
	  async delete(request) {
	    await del(
	      this.fetch,
	      `${this.config.host}/api/delete`,
	      { name: request.model },
	      { headers: this.config.headers }
	    );
	    return { status: "success" };
	  }
	  /**
	   * Copies a model from one name to another. The request object should contain the name of the
	   * model to copy and the new name.
	   * @param request {CopyRequest} - The request object.
	   * @returns {Promise<StatusResponse>} - The response object.
	   */
	  async copy(request) {
	    await post(this.fetch, `${this.config.host}/api/copy`, { ...request }, {
	      headers: this.config.headers
	    });
	    return { status: "success" };
	  }
	  /**
	   * Lists the models on the server.
	   * @returns {Promise<ListResponse>} - The response object.
	   * @throws {Error} - If the response body is missing.
	   */
	  async list() {
	    const response = await get(this.fetch, `${this.config.host}/api/tags`, {
	      headers: this.config.headers
	    });
	    return await response.json();
	  }
	  /**
	   * Shows the metadata of a model. The request object should contain the name of the model.
	   * @param request {ShowRequest} - The request object.
	   * @returns {Promise<ShowResponse>} - The response object.
	   */
	  async show(request) {
	    const response = await post(this.fetch, `${this.config.host}/api/show`, {
	      ...request
	    }, {
	      headers: this.config.headers
	    });
	    return await response.json();
	  }
	  /**
	   * Embeds text input into vectors.
	   * @param request {EmbedRequest} - The request object.
	   * @returns {Promise<EmbedResponse>} - The response object.
	   */
	  async embed(request) {
	    const response = await post(this.fetch, `${this.config.host}/api/embed`, {
	      ...request
	    }, {
	      headers: this.config.headers
	    });
	    return await response.json();
	  }
	  /**
	   * Embeds a text prompt into a vector.
	   * @param request {EmbeddingsRequest} - The request object.
	   * @returns {Promise<EmbeddingsResponse>} - The response object.
	   */
	  async embeddings(request) {
	    const response = await post(this.fetch, `${this.config.host}/api/embeddings`, {
	      ...request
	    }, {
	      headers: this.config.headers
	    });
	    return await response.json();
	  }
	  /**
	   * Lists the running models on the server
	   * @returns {Promise<ListResponse>} - The response object.
	   * @throws {Error} - If the response body is missing.
	   */
	  async ps() {
	    const response = await get(this.fetch, `${this.config.host}/api/ps`, {
	      headers: this.config.headers
	    });
	    return await response.json();
	  }
	  /**
	   * Returns the Ollama server version.
	   * @returns {Promise<VersionResponse>} - The server version object.
	   */
	  async version() {
	    const response = await get(this.fetch, `${this.config.host}/api/version`, {
	      headers: this.config.headers
	    });
	    return await response.json();
	  }
	  /**
	   * Performs web search using the Ollama web search API
	   * @param request {WebSearchRequest} - The search request containing query and options
	   * @returns {Promise<WebSearchResponse>} - The search results
	   * @throws {Error} - If the request is invalid or the server returns an error
	   */
	  async webSearch(request) {
	    if (!request.query || request.query.length === 0) {
	      throw new Error("Query is required");
	    }
	    const response = await post(this.fetch, `https://ollama.com/api/web_search`, { ...request }, {
	      headers: this.config.headers
	    });
	    return await response.json();
	  }
	  /**
	   * Fetches a single page using the Ollama web fetch API
	   * @param request {WebFetchRequest} - The fetch request containing a URL
	   * @returns {Promise<WebFetchResponse>} - The fetch result
	   * @throws {Error} - If the request is invalid or the server returns an error
	   */
	  async webFetch(request) {
	    if (!request.url || request.url.length === 0) {
	      throw new Error("URL is required");
	    }
	    const response = await post(this.fetch, `https://ollama.com/api/web_fetch`, { ...request }, { headers: this.config.headers });
	    return await response.json();
	  }
	};
	const browser$1 = new Ollama$1();

	browser.Ollama = Ollama$1;
	browser.default = browser$1;
	return browser;
}

var hasRequiredDist;

function requireDist () {
	if (hasRequiredDist) return dist;
	hasRequiredDist = 1;

	Object.defineProperty(dist, '__esModule', { value: true });

	const fs = require$$0;
	const node_path = require$$1;
	const browser = requireBrowser();


	function _interopDefaultCompat (e) { return e && typeof e === 'object' && 'default' in e ? e.default : e; }

	const fs__default = /*#__PURE__*/_interopDefaultCompat(fs);

	class Ollama extends browser.Ollama {
	  async encodeImage(image) {
	    if (typeof image !== "string") {
	      return Buffer.from(image).toString("base64");
	    }
	    try {
	      if (fs__default.existsSync(image)) {
	        const fileBuffer = await fs.promises.readFile(node_path.resolve(image));
	        return Buffer.from(fileBuffer).toString("base64");
	      }
	    } catch {
	    }
	    return image;
	  }
	  /**
	   * checks if a file exists
	   * @param path {string} - The path to the file
	   * @private @internal
	   * @returns {Promise<boolean>} - Whether the file exists or not
	   */
	  async fileExists(path) {
	    try {
	      await fs.promises.access(path);
	      return true;
	    } catch {
	      return false;
	    }
	  }
	  async create(request) {
	    if (request.from && await this.fileExists(node_path.resolve(request.from))) {
	      throw Error("Creating with a local path is not currently supported from ollama-js");
	    }
	    if (request.stream) {
	      return super.create(request);
	    } else {
	      return super.create(request);
	    }
	  }
	}
	const index = new Ollama();

	dist.Ollama = Ollama;
	dist.default = index;
	return dist;
}

var ollama;
var hasRequiredOllama;

function requireOllama () {
	if (hasRequiredOllama) return ollama;
	hasRequiredOllama = 1;
	var __defProp = Object.defineProperty;
	var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
	var __getOwnPropNames = Object.getOwnPropertyNames;
	var __hasOwnProp = Object.prototype.hasOwnProperty;
	var __export = (target, all) => {
	  for (var name in all)
	    __defProp(target, name, { get: all[name], enumerable: true });
	};
	var __copyProps = (to, from, except, desc) => {
	  if (from && typeof from === "object" || typeof from === "function") {
	    for (let key of __getOwnPropNames(from))
	      if (!__hasOwnProp.call(to, key) && key !== except)
	        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
	  }
	  return to;
	};
	var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
	var ollama_exports = {};
	__export(ollama_exports, {
	  embedText: () => embedText,
	  listModels: () => listModels
	});
	ollama = __toCommonJS(ollama_exports);
	var import_ollama = requireDist();
	async function listModels(url) {
	  const ollama = new import_ollama.Ollama({ host: url });
	  const response = await ollama.list();
	  return response.models.map((m) => m.name);
	}
	async function embedText(url, model, text) {
	  const ollama = new import_ollama.Ollama({ host: url });
	  const response = await ollama.embeddings({
	    model,
	    prompt: text
	  });
	  return response.embedding;
	}
	return ollama;
}

var server;
var hasRequiredServer;

function requireServer () {
	if (hasRequiredServer) return server;
	hasRequiredServer = 1;
	var __defProp = Object.defineProperty;
	var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
	var __getOwnPropNames = Object.getOwnPropertyNames;
	var __hasOwnProp = Object.prototype.hasOwnProperty;
	var __export = (target, all) => {
	  for (var name in all)
	    __defProp(target, name, { get: all[name], enumerable: true });
	};
	var __copyProps = (to, from, except, desc) => {
	  if (from && typeof from === "object" || typeof from === "function") {
	    for (let key of __getOwnPropNames(from))
	      if (!__hasOwnProp.call(to, key) && key !== except)
	        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
	  }
	  return to;
	};
	var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
	var server_exports = {};
	__export(server_exports, {
	  HttpSearchServer: () => HttpSearchServer
	});
	server = __toCommonJS(server_exports);
	var import_node_buffer = require$$0$1;
	var import_node_crypto = require$$1$1;
	var import_node_http = require$$2;
	var import_ollama = requireOllama();
	class HttpError extends Error {
	  status;
	  payload;
	  constructor(status, payload) {
	    super(payload.error);
	    this.status = status;
	    this.payload = payload;
	  }
	}
	function computeSha256(content) {
	  const hash = (0, import_node_crypto.createHash)("sha256").update(import_node_buffer.Buffer.from(content, "utf8")).digest("hex");
	  return `sha256:${hash}`;
	}
	function splitLines(content) {
	  if (content.length === 0) {
	    return { lines: [], trailingNewline: false };
	  }
	  const trailingNewline = content.endsWith("\n");
	  const lines = content.split("\n");
	  if (trailingNewline) {
	    lines.pop();
	  }
	  return { lines, trailingNewline };
	}
	function splitReplacement(replacement) {
	  if (replacement.length === 0) {
	    return [];
	  }
	  const lines = replacement.split("\n");
	  if (replacement.endsWith("\n")) {
	    lines.pop();
	  }
	  return lines;
	}
	function joinLines(lines, trailingNewline) {
	  const content = lines.join("\n");
	  if (trailingNewline && lines.length > 0) {
	    return `${content}
`;
	  }
	  return content;
	}
	function parseLineNumber(value, key) {
	  if (typeof value !== "number" || !Number.isInteger(value)) {
	    throw new HttpError(400, { error: `invalid_${key}` });
	  }
	  return value;
	}
	function parseRequiredString(value, key) {
	  if (typeof value !== "string" || value.length === 0) {
	    throw new HttpError(400, { error: `invalid_${key}` });
	  }
	  return value;
	}
	function parseStringField(value, key) {
	  if (typeof value !== "string") {
	    throw new HttpError(400, { error: `invalid_${key}` });
	  }
	  return value;
	}
	function parseMarkdownPath(value) {
	  const path = parseRequiredString(value, "path");
	  if (!path.endsWith(".md")) {
	    throw new HttpError(400, { error: "invalid_path" });
	  }
	  return path;
	}
	function parseJsonBody(rawBody) {
	  try {
	    const body = JSON.parse(rawBody);
	    if (!body || typeof body !== "object" || Array.isArray(body)) {
	      throw new HttpError(400, { error: "invalid_body" });
	    }
	    return body;
	  } catch (error) {
	    if (error instanceof HttpError) {
	      throw error;
	    }
	    throw new HttpError(400, { error: "invalid_json" });
	  }
	}
	class HttpSearchServer {
	  server;
	  index;
	  ollamaUrl;
	  model;
	  noteAccess;
	  constructor(index, ollamaUrl, model, noteAccess) {
	    this.index = index;
	    this.ollamaUrl = ollamaUrl;
	    this.model = model;
	    this.noteAccess = noteAccess;
	  }
	  updateConfig(ollamaUrl, model) {
	    this.ollamaUrl = ollamaUrl;
	    this.model = model;
	  }
	  async handleRead(body) {
	    const path = parseMarkdownPath(body.path);
	    const snapshot = await this.noteAccess.readNote(path);
	    if (!snapshot) {
	      throw new HttpError(404, { error: "note_not_found", path });
	    }
	    const { lines } = splitLines(snapshot.content);
	    return {
	      path: snapshot.path,
	      content: snapshot.content,
	      line_count: lines.length,
	      content_hash: computeSha256(snapshot.content),
	      mtime: snapshot.mtime
	    };
	  }
	  async handlePatchLines(body) {
	    const path = parseMarkdownPath(body.path);
	    const startLine = parseLineNumber(body.start_line, "start_line");
	    const endLine = parseLineNumber(body.end_line, "end_line");
	    const replacement = parseStringField(body.replacement, "replacement");
	    const expectedHash = parseRequiredString(body.expected_hash, "expected_hash");
	    if (startLine < 1 || endLine < startLine) {
	      throw new HttpError(400, { error: "invalid_line_range" });
	    }
	    const currentSnapshot = await this.noteAccess.readNote(path);
	    if (!currentSnapshot) {
	      throw new HttpError(404, { error: "note_not_found", path });
	    }
	    const currentHash = computeSha256(currentSnapshot.content);
	    if (currentHash !== expectedHash) {
	      throw new HttpError(409, {
	        error: "hash_mismatch",
	        path,
	        expected_hash: expectedHash,
	        current_hash: currentHash,
	        mtime: currentSnapshot.mtime
	      });
	    }
	    const { lines, trailingNewline } = splitLines(currentSnapshot.content);
	    if (endLine > lines.length) {
	      throw new HttpError(400, { error: "line_range_out_of_bounds" });
	    }
	    const replacementLines = splitReplacement(replacement);
	    const updatedLines = [
	      ...lines.slice(0, startLine - 1),
	      ...replacementLines,
	      ...lines.slice(endLine)
	    ];
	    const updatedContent = joinLines(updatedLines, trailingNewline);
	    const writeResult = await this.noteAccess.writeNote(path, updatedContent);
	    if (!writeResult) {
	      throw new HttpError(404, { error: "note_not_found", path });
	    }
	    await this.noteAccess.reindexNote(path);
	    return {
	      path: writeResult.path,
	      applied_start_line: startLine,
	      applied_end_line: endLine,
	      new_hash: computeSha256(updatedContent),
	      new_line_count: updatedLines.length,
	      mtime: writeResult.mtime
	    };
	  }
	  start(port) {
	    this.server = (0, import_node_http.createServer)(async (req, res) => {
	      res.setHeader("Access-Control-Allow-Origin", "*");
	      res.setHeader("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS");
	      res.setHeader("Access-Control-Allow-Headers", "Content-Type");
	      if (req.method === "OPTIONS") {
	        res.writeHead(204);
	        res.end();
	        return;
	      }
	      const url = new URL(req.url || "", `http://${req.headers.host}`);
	      const pathname = url.pathname;
	      if (req.method === "GET") {
	        try {
	          if (pathname === "/notes/read") {
	            const data = { path: url.searchParams.get("path") };
	            const note = await this.handleRead(data);
	            res.writeHead(200, { "Content-Type": "application/json" });
	            res.end(JSON.stringify(note));
	          } else {
	            res.writeHead(404);
	            res.end();
	          }
	        } catch (error) {
	          this.handleError(res, error);
	        }
	      } else if (req.method === "POST" || req.method === "PATCH") {
	        let body = "";
	        req.on("data", (chunk) => {
	          body += chunk.toString();
	        });
	        req.on("end", async () => {
	          try {
	            const data = parseJsonBody(body);
	            if (req.method === "POST" && pathname === "/embed") {
	              const text = parseRequiredString(data.text, "text");
	              const vector = await (0, import_ollama.embedText)(this.ollamaUrl, this.model, text);
	              res.writeHead(200, { "Content-Type": "application/json" });
	              res.end(JSON.stringify({ vector }));
	            } else if (req.method === "POST" && pathname === "/search/vector") {
	              const results = this.index.search(data.vector, data.allowlist, data.top_n);
	              res.writeHead(200, { "Content-Type": "application/json" });
	              res.end(JSON.stringify({ results }));
	            } else if (req.method === "POST" && pathname === "/search/text") {
	              const text = parseRequiredString(data.text, "text");
	              const vector = await (0, import_ollama.embedText)(this.ollamaUrl, this.model, text);
	              const results = this.index.search(vector, data.allowlist, data.top_n);
	              res.writeHead(200, { "Content-Type": "application/json" });
	              res.end(JSON.stringify({ results }));
	            } else if (req.method === "PATCH" && pathname === "/notes/patch-lines") {
	              const patched = await this.handlePatchLines(data);
	              res.writeHead(200, { "Content-Type": "application/json" });
	              res.end(JSON.stringify(patched));
	            } else {
	              res.writeHead(404);
	              res.end();
	            }
	          } catch (error) {
	            this.handleError(res, error);
	          }
	        });
	      } else {
	        res.writeHead(405);
	        res.end();
	      }
	    });
	    this.server.listen(port, "127.0.0.1");
	  }
	  handleError(res, error) {
	    if (error instanceof HttpError) {
	      res.writeHead(error.status, { "Content-Type": "application/json" });
	      res.end(JSON.stringify(error.payload));
	      return;
	    }
	    const message = error instanceof Error ? error.message : String(error);
	    res.writeHead(500, { "Content-Type": "application/json" });
	    res.end(JSON.stringify({ error: message }));
	  }
	  stop() {
	    if (this.server) {
	      this.server.close();
	    }
	  }
	}
	return server;
}

var settings;
var hasRequiredSettings;

function requireSettings () {
	if (hasRequiredSettings) return settings;
	hasRequiredSettings = 1;
	var __defProp = Object.defineProperty;
	var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
	var __getOwnPropNames = Object.getOwnPropertyNames;
	var __hasOwnProp = Object.prototype.hasOwnProperty;
	var __export = (target, all) => {
	  for (var name in all)
	    __defProp(target, name, { get: all[name], enumerable: true });
	};
	var __copyProps = (to, from, except, desc) => {
	  if (from && typeof from === "object" || typeof from === "function") {
	    for (let key of __getOwnPropNames(from))
	      if (!__hasOwnProp.call(to, key) && key !== except)
	        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
	  }
	  return to;
	};
	var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
	var settings_exports = {};
	__export(settings_exports, {
	  DEFAULT_SETTINGS: () => DEFAULT_SETTINGS
	});
	settings = __toCommonJS(settings_exports);
	const DEFAULT_SETTINGS = {
	  ollamaUrl: "http://localhost:11434",
	  ollamaToken: "",
	  embeddingModel: "",
	  serverPort: 51362,
	  minChars: 100
	};
	return settings;
}

var settingsTab;
var hasRequiredSettingsTab;

function requireSettingsTab () {
	if (hasRequiredSettingsTab) return settingsTab;
	hasRequiredSettingsTab = 1;
	var __defProp = Object.defineProperty;
	var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
	var __getOwnPropNames = Object.getOwnPropertyNames;
	var __hasOwnProp = Object.prototype.hasOwnProperty;
	var __export = (target, all) => {
	  for (var name in all)
	    __defProp(target, name, { get: all[name], enumerable: true });
	};
	var __copyProps = (to, from, except, desc) => {
	  if (from && typeof from === "object" || typeof from === "function") {
	    for (let key of __getOwnPropNames(from))
	      if (!__hasOwnProp.call(to, key) && key !== except)
	        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
	  }
	  return to;
	};
	var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
	var settingsTab_exports = {};
	__export(settingsTab_exports, {
	  VectorSearchSettingsTab: () => VectorSearchSettingsTab
	});
	settingsTab = __toCommonJS(settingsTab_exports);
	var import_obsidian = require$$0$2;
	var import_ollama = requireOllama();
	class VectorSearchSettingsTab extends import_obsidian.PluginSettingTab {
	  plugin;
	  constructor(app, plugin) {
	    super(app, plugin);
	    this.plugin = plugin;
	  }
	  display() {
	    const { containerEl } = this;
	    containerEl.empty();
	    new import_obsidian.Setting(containerEl).setName("Ollama URL").setDesc("Endpoint for your local Ollama instance").addText((text) => text.setPlaceholder("http://localhost:11434").setValue(this.plugin.settings.ollamaUrl).onChange(async (value) => {
	      this.plugin.settings.ollamaUrl = value;
	      await this.plugin.saveSettings();
	      this.display();
	    }));
	    const modelSetting = new import_obsidian.Setting(containerEl).setName("Embedding Model").setDesc("Select the model to use for embeddings");
	    (0, import_ollama.listModels)(this.plugin.settings.ollamaUrl).then((models) => {
	      modelSetting.addDropdown((dropdown) => {
	        dropdown.addOption("", "Select a model");
	        models.forEach((model) => dropdown.addOption(model, model));
	        dropdown.setValue(this.plugin.settings.embeddingModel);
	        dropdown.onChange(async (value) => {
	          this.plugin.settings.embeddingModel = value;
	          await this.plugin.saveSettings();
	          this.plugin.server.updateConfig(this.plugin.settings.ollamaUrl, value);
	          if (value) {
	            new import_obsidian.Setting(containerEl).setName("Re-index required").setDesc("Changing the model requires a full re-index of your vault.").addButton((btn) => btn.setButtonText("Re-index All").onClick(async () => {
	              await this.plugin.reindexAll();
	            }));
	          }
	        });
	      });
	    }).catch((_err) => {
	      modelSetting.setDesc("Error connecting to Ollama. Make sure it is running.");
	    });
	    new import_obsidian.Setting(containerEl).setName("HTTP Server Port").setDesc("Port for the local search API").addText((text) => text.setPlaceholder("51362").setValue(String(this.plugin.settings.serverPort)).onChange(async (value) => {
	      this.plugin.settings.serverPort = Number(value);
	      await this.plugin.saveSettings();
	    }));
	    new import_obsidian.Setting(containerEl).setName("Minimum Characters").setDesc("Notes shorter than this will be skipped during indexing").addText((text) => text.setPlaceholder("100").setValue(String(this.plugin.settings.minChars)).onChange(async (value) => {
	      this.plugin.settings.minChars = Number(value);
	      await this.plugin.saveSettings();
	    }));
	    const usage = this.plugin.index.sizeInBytes();
	    new import_obsidian.Setting(containerEl).setName("Index Storage Usage").setDesc(`Currently using ${(usage / 1024 / 1024).toFixed(2)} MB on disk`).addButton((btn) => btn.setButtonText("Refresh Usage").onClick(() => this.display()));
	    new import_obsidian.Setting(containerEl).setName("Force Re-index").setDesc("Trigger a full re-index of the vault").addButton((btn) => btn.setButtonText("Re-index All Now").setWarning().onClick(async () => {
	      await this.plugin.reindexAll();
	    }));
	  }
	}
	return settingsTab;
}

var main$1;
var hasRequiredMain;

function requireMain () {
	if (hasRequiredMain) return main$1;
	hasRequiredMain = 1;
	var __defProp = Object.defineProperty;
	var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
	var __getOwnPropNames = Object.getOwnPropertyNames;
	var __hasOwnProp = Object.prototype.hasOwnProperty;
	var __export = (target, all) => {
	  for (var name in all)
	    __defProp(target, name, { get: all[name], enumerable: true });
	};
	var __copyProps = (to, from, except, desc) => {
	  if (from && typeof from === "object" || typeof from === "function") {
	    for (let key of __getOwnPropNames(from))
	      if (!__hasOwnProp.call(to, key) && key !== except)
	        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
	  }
	  return to;
	};
	var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
	var main_exports = {};
	__export(main_exports, {
	  default: () => VectorSearchPlugin
	});
	main$1 = __toCommonJS(main_exports);
	var import_obsidian = require$$0$2;
	var import_index = requireSrc();
	var import_ollama = requireOllama();
	var import_server = requireServer();
	var import_settings = requireSettings();
	var import_settingsTab = requireSettingsTab();
	class VectorSearchPlugin extends import_obsidian.Plugin {
	  settings;
	  index;
	  server;
	  async onload() {
	    await this.loadSettings();
	    this.index = new import_index.NoteIndex();
	    await this.loadIndex();
	    this.server = new import_server.HttpSearchServer(
	      this.index,
	      this.settings.ollamaUrl,
	      this.settings.embeddingModel,
	      {
	        readNote: async (path) => this.readNote(path),
	        writeNote: async (path, content) => this.writeNote(path, content),
	        reindexNote: async (path) => this.reindexNote(path)
	      }
	    );
	    this.server.start(this.settings.serverPort);
	    this.addSettingTab(new import_settingsTab.VectorSearchSettingsTab(this.app, this));
	    this.app.workspace.onLayoutReady(() => {
	      this.incrementalIndex();
	    });
	    this.registerEvent(
	      this.app.vault.on("modify", async (file) => {
	        if (file instanceof import_obsidian.TFile && file.extension === "md") {
	          await this.indexFile(file);
	          await this.saveIndex();
	        }
	      })
	    );
	    this.registerEvent(
	      this.app.vault.on("create", async (file) => {
	        if (file instanceof import_obsidian.TFile && file.extension === "md") {
	          await this.indexFile(file);
	          await this.saveIndex();
	        }
	      })
	    );
	    this.registerEvent(
	      this.app.vault.on("delete", async (file) => {
	        if (file instanceof import_obsidian.TFile) {
	          this.index.delete(file.path);
	          await this.saveIndex();
	        }
	      })
	    );
	    this.registerEvent(
	      this.app.vault.on("rename", async (file, oldPath) => {
	        if (file instanceof import_obsidian.TFile && file.extension === "md") {
	          this.index.delete(oldPath);
	          await this.indexFile(file);
	          await this.saveIndex();
	        }
	      })
	    );
	  }
	  onunload() {
	    this.server.stop();
	  }
	  async loadSettings() {
	    this.settings = Object.assign({}, import_settings.DEFAULT_SETTINGS, await this.loadData());
	  }
	  async saveSettings() {
	    await this.saveData(this.settings);
	  }
	  async loadIndex() {
	    const indexPath = this.getIndexFilePath();
	    if (await this.app.vault.adapter.exists(indexPath)) {
	      const data = await this.app.vault.adapter.read(indexPath);
	      this.index.deserialize(data);
	    }
	  }
	  async saveIndex() {
	    const indexPath = this.getIndexFilePath();
	    await this.app.vault.adapter.write(indexPath, this.index.serialize());
	  }
	  getIndexFilePath() {
	    return `${this.manifest.dir}/index.json`;
	  }
	  getMarkdownFile(path) {
	    const abstractFile = this.app.vault.getAbstractFileByPath(path);
	    if (!(abstractFile instanceof import_obsidian.TFile) || abstractFile.extension !== "md") {
	      return null;
	    }
	    return abstractFile;
	  }
	  async readNote(path) {
	    const file = this.getMarkdownFile(path);
	    if (!file) {
	      return null;
	    }
	    const content = await this.app.vault.read(file);
	    return {
	      path: file.path,
	      content,
	      mtime: file.stat.mtime
	    };
	  }
	  async writeNote(path, content) {
	    const file = this.getMarkdownFile(path);
	    if (!file) {
	      return null;
	    }
	    await this.app.vault.modify(file, content);
	    const refreshed = this.getMarkdownFile(path);
	    if (!refreshed) {
	      return null;
	    }
	    return {
	      path: refreshed.path,
	      content,
	      mtime: refreshed.stat.mtime
	    };
	  }
	  async reindexNote(path) {
	    const file = this.getMarkdownFile(path);
	    if (!file) {
	      return;
	    }
	    await this.indexFile(file);
	    await this.saveIndex();
	  }
	  async indexFile(file) {
	    if (!this.settings.embeddingModel)
	      return;
	    const content = await this.app.vault.read(file);
	    if (content.length < this.settings.minChars) {
	      this.index.delete(file.path);
	      return;
	    }
	    try {
	      const vector = await (0, import_ollama.embedText)(
	        this.settings.ollamaUrl,
	        this.settings.embeddingModel,
	        content
	      );
	      this.index.set(file.path, {
	        path: file.path,
	        vector,
	        mtime: file.stat.mtime
	      });
	    } catch (e) {
	      console.error(`Failed to embed ${file.path}`, e);
	    }
	  }
	  async incrementalIndex() {
	    if (!this.settings.embeddingModel) {
	      new import_obsidian.Notice("Vector Search: Select an embedding model in settings to enable search.");
	      return;
	    }
	    const files = this.app.vault.getMarkdownFiles();
	    const toIndex = files.filter((f) => {
	      const entry = this.index.get(f.path);
	      return !entry || entry.mtime < f.stat.mtime;
	    });
	    if (toIndex.length === 0)
	      return;
	    new import_obsidian.Notice(`Vector Search: Updating index for ${toIndex.length} files...`);
	    let done = 0;
	    for (const file of toIndex) {
	      await this.indexFile(file);
	      done++;
	      if (done % 10 === 0) {
	        console.log(`Indexed ${done}/${toIndex.length}`);
	      }
	    }
	    await this.saveIndex();
	    new import_obsidian.Notice("Vector Search: Index update complete.");
	  }
	  async reindexAll() {
	    if (!this.settings.embeddingModel) {
	      new import_obsidian.Notice("Vector Search: Select a model first.");
	      return;
	    }
	    this.index.clear();
	    const files = this.app.vault.getMarkdownFiles();
	    new import_obsidian.Notice(`Vector Search: Full re-index started (${files.length} files)...`);
	    let done = 0;
	    for (const file of files) {
	      await this.indexFile(file);
	      done++;
	      if (done % 10 === 0) {
	        console.log(`Re-indexing ${done}/${files.length}`);
	      }
	    }
	    await this.saveIndex();
	    new import_obsidian.Notice("Vector Search: Full re-index complete.");
	  }
	}
	return main$1;
}

var mainExports = requireMain();
const main = /*@__PURE__*/getDefaultExportFromCjs(mainExports);

module.exports = main;
//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoibWFpbi5qcyIsInNvdXJjZXMiOlsiLi4vc3JjL2luZGV4LnRzIiwiLi4vbm9kZV9tb2R1bGVzLy5wbnBtL3doYXR3Zy1mZXRjaEAzLjYuMjAvbm9kZV9tb2R1bGVzL3doYXR3Zy1mZXRjaC9mZXRjaC5qcyIsIi4uL25vZGVfbW9kdWxlcy8ucG5wbS9vbGxhbWFAMC42LjMvbm9kZV9tb2R1bGVzL29sbGFtYS9kaXN0L2Jyb3dzZXIuY2pzIiwiLi4vbm9kZV9tb2R1bGVzLy5wbnBtL29sbGFtYUAwLjYuMy9ub2RlX21vZHVsZXMvb2xsYW1hL2Rpc3QvaW5kZXguY2pzIiwiLi4vc3JjL29sbGFtYS50cyIsIi4uL3NyYy9zZXJ2ZXIudHMiLCIuLi9zcmMvc2V0dGluZ3MudHMiLCIuLi9zcmMvc2V0dGluZ3NUYWIudHMiLCIuLi9zcmMvbWFpbi50cyIsIi4uL3NyYy9tYWluLnRzP2NvbW1vbmpzLWVudHJ5Il0sInNvdXJjZXNDb250ZW50IjpbImV4cG9ydCBpbnRlcmZhY2UgSW5kZXhFbnRyeSB7XG4gIHBhdGg6IHN0cmluZ1xuICB2ZWN0b3I6IG51bWJlcltdXG4gIG10aW1lOiBudW1iZXJcbn1cblxuZXhwb3J0IGNsYXNzIE5vdGVJbmRleCB7XG4gIHByaXZhdGUgZW50cmllczogTWFwPHN0cmluZywgSW5kZXhFbnRyeT4gPSBuZXcgTWFwKClcblxuICBjb25zdHJ1Y3RvcigpIHt9XG5cbiAgcHVibGljIHNldChwYXRoOiBzdHJpbmcsIGVudHJ5OiBJbmRleEVudHJ5KSB7XG4gICAgdGhpcy5lbnRyaWVzLnNldChwYXRoLCBlbnRyeSlcbiAgfVxuXG4gIHB1YmxpYyBkZWxldGUocGF0aDogc3RyaW5nKSB7XG4gICAgdGhpcy5lbnRyaWVzLmRlbGV0ZShwYXRoKVxuICB9XG5cbiAgcHVibGljIGdldChwYXRoOiBzdHJpbmcpOiBJbmRleEVudHJ5IHwgdW5kZWZpbmVkIHtcbiAgICByZXR1cm4gdGhpcy5lbnRyaWVzLmdldChwYXRoKVxuICB9XG5cbiAgcHVibGljIGNsZWFyKCkge1xuICAgIHRoaXMuZW50cmllcy5jbGVhcigpXG4gIH1cblxuICBwdWJsaWMgZ2V0QWxsKCk6IEluZGV4RW50cnlbXSB7XG4gICAgcmV0dXJuIEFycmF5LmZyb20odGhpcy5lbnRyaWVzLnZhbHVlcygpKVxuICB9XG5cbiAgcHVibGljIHNlYXJjaChxdWVyeVZlY3RvcjogbnVtYmVyW10sIGFsbG93bGlzdD86IHN0cmluZ1tdLCB0b3BOOiBudW1iZXIgPSAxMCk6IHsgcGF0aDogc3RyaW5nLCBzY29yZTogbnVtYmVyIH1bXSB7XG4gICAgbGV0IGNhbmRpZGF0ZXMgPSB0aGlzLmdldEFsbCgpXG4gICAgaWYgKGFsbG93bGlzdCAmJiBhbGxvd2xpc3QubGVuZ3RoID4gMCkge1xuICAgICAgY29uc3Qgc2V0ID0gbmV3IFNldChhbGxvd2xpc3QpXG4gICAgICBjYW5kaWRhdGVzID0gY2FuZGlkYXRlcy5maWx0ZXIoZSA9PiBzZXQuaGFzKGUucGF0aCkpXG4gICAgfVxuXG4gICAgY29uc3QgcmVzdWx0cyA9IGNhbmRpZGF0ZXMubWFwKGVudHJ5ID0+ICh7XG4gICAgICBwYXRoOiBlbnRyeS5wYXRoLFxuICAgICAgc2NvcmU6IHRoaXMuY29zaW5lU2ltaWxhcml0eShxdWVyeVZlY3RvciwgZW50cnkudmVjdG9yKSxcbiAgICB9KSlcblxuICAgIHJldHVybiByZXN1bHRzXG4gICAgICAuc29ydCgoYSwgYikgPT4gYi5zY29yZSAtIGEuc2NvcmUpXG4gICAgICAuc2xpY2UoMCwgdG9wTilcbiAgfVxuXG4gIHByaXZhdGUgY29zaW5lU2ltaWxhcml0eSh2MTogbnVtYmVyW10sIHYyOiBudW1iZXJbXSk6IG51bWJlciB7XG4gICAgbGV0IGRvdFByb2R1Y3QgPSAwXG4gICAgbGV0IG1hZzEgPSAwXG4gICAgbGV0IG1hZzIgPSAwXG4gICAgZm9yIChsZXQgaSA9IDA7IGkgPCB2MS5sZW5ndGg7IGkrKykge1xuICAgICAgZG90UHJvZHVjdCArPSB2MVtpXSAqIHYyW2ldXG4gICAgICBtYWcxICs9IHYxW2ldICogdjFbaV1cbiAgICAgIG1hZzIgKz0gdjJbaV0gKiB2MltpXVxuICAgIH1cbiAgICBtYWcxID0gTWF0aC5zcXJ0KG1hZzEpXG4gICAgbWFnMiA9IE1hdGguc3FydChtYWcyKVxuICAgIGlmIChtYWcxID09PSAwIHx8IG1hZzIgPT09IDApXG4gICAgICByZXR1cm4gMFxuICAgIHJldHVybiBkb3RQcm9kdWN0IC8gKG1hZzEgKiBtYWcyKVxuICB9XG5cbiAgcHVibGljIHNlcmlhbGl6ZSgpOiBzdHJpbmcge1xuICAgIHJldHVybiBKU09OLnN0cmluZ2lmeShBcnJheS5mcm9tKHRoaXMuZW50cmllcy52YWx1ZXMoKSkpXG4gIH1cblxuICBwdWJsaWMgZGVzZXJpYWxpemUoanNvbjogc3RyaW5nKSB7XG4gICAgdHJ5IHtcbiAgICAgIGNvbnN0IGRhdGE6IEluZGV4RW50cnlbXSA9IEpTT04ucGFyc2UoanNvbilcbiAgICAgIHRoaXMuZW50cmllcy5jbGVhcigpXG4gICAgICBmb3IgKGNvbnN0IGVudHJ5IG9mIGRhdGEpIHtcbiAgICAgICAgdGhpcy5lbnRyaWVzLnNldChlbnRyeS5wYXRoLCBlbnRyeSlcbiAgICAgIH1cbiAgICB9XG4gICAgY2F0Y2ggKGUpIHtcbiAgICAgIGNvbnNvbGUuZXJyb3IoJ0ZhaWxlZCB0byBkZXNlcmlhbGl6ZSBpbmRleCcsIGUpXG4gICAgfVxuICB9XG5cbiAgcHVibGljIHNpemVJbkJ5dGVzKCk6IG51bWJlciB7XG4gICAgcmV0dXJuIG5ldyBUZXh0RW5jb2RlcigpLmVuY29kZSh0aGlzLnNlcmlhbGl6ZSgpKS5sZW5ndGhcbiAgfVxufVxuIiwiLyogZXNsaW50LWRpc2FibGUgbm8tcHJvdG90eXBlLWJ1aWx0aW5zICovXG52YXIgZyA9XG4gICh0eXBlb2YgZ2xvYmFsVGhpcyAhPT0gJ3VuZGVmaW5lZCcgJiYgZ2xvYmFsVGhpcykgfHxcbiAgKHR5cGVvZiBzZWxmICE9PSAndW5kZWZpbmVkJyAmJiBzZWxmKSB8fFxuICAvLyBlc2xpbnQtZGlzYWJsZS1uZXh0LWxpbmUgbm8tdW5kZWZcbiAgKHR5cGVvZiBnbG9iYWwgIT09ICd1bmRlZmluZWQnICYmIGdsb2JhbCkgfHxcbiAge31cblxudmFyIHN1cHBvcnQgPSB7XG4gIHNlYXJjaFBhcmFtczogJ1VSTFNlYXJjaFBhcmFtcycgaW4gZyxcbiAgaXRlcmFibGU6ICdTeW1ib2wnIGluIGcgJiYgJ2l0ZXJhdG9yJyBpbiBTeW1ib2wsXG4gIGJsb2I6XG4gICAgJ0ZpbGVSZWFkZXInIGluIGcgJiZcbiAgICAnQmxvYicgaW4gZyAmJlxuICAgIChmdW5jdGlvbigpIHtcbiAgICAgIHRyeSB7XG4gICAgICAgIG5ldyBCbG9iKClcbiAgICAgICAgcmV0dXJuIHRydWVcbiAgICAgIH0gY2F0Y2ggKGUpIHtcbiAgICAgICAgcmV0dXJuIGZhbHNlXG4gICAgICB9XG4gICAgfSkoKSxcbiAgZm9ybURhdGE6ICdGb3JtRGF0YScgaW4gZyxcbiAgYXJyYXlCdWZmZXI6ICdBcnJheUJ1ZmZlcicgaW4gZ1xufVxuXG5mdW5jdGlvbiBpc0RhdGFWaWV3KG9iaikge1xuICByZXR1cm4gb2JqICYmIERhdGFWaWV3LnByb3RvdHlwZS5pc1Byb3RvdHlwZU9mKG9iailcbn1cblxuaWYgKHN1cHBvcnQuYXJyYXlCdWZmZXIpIHtcbiAgdmFyIHZpZXdDbGFzc2VzID0gW1xuICAgICdbb2JqZWN0IEludDhBcnJheV0nLFxuICAgICdbb2JqZWN0IFVpbnQ4QXJyYXldJyxcbiAgICAnW29iamVjdCBVaW50OENsYW1wZWRBcnJheV0nLFxuICAgICdbb2JqZWN0IEludDE2QXJyYXldJyxcbiAgICAnW29iamVjdCBVaW50MTZBcnJheV0nLFxuICAgICdbb2JqZWN0IEludDMyQXJyYXldJyxcbiAgICAnW29iamVjdCBVaW50MzJBcnJheV0nLFxuICAgICdbb2JqZWN0IEZsb2F0MzJBcnJheV0nLFxuICAgICdbb2JqZWN0IEZsb2F0NjRBcnJheV0nXG4gIF1cblxuICB2YXIgaXNBcnJheUJ1ZmZlclZpZXcgPVxuICAgIEFycmF5QnVmZmVyLmlzVmlldyB8fFxuICAgIGZ1bmN0aW9uKG9iaikge1xuICAgICAgcmV0dXJuIG9iaiAmJiB2aWV3Q2xhc3Nlcy5pbmRleE9mKE9iamVjdC5wcm90b3R5cGUudG9TdHJpbmcuY2FsbChvYmopKSA+IC0xXG4gICAgfVxufVxuXG5mdW5jdGlvbiBub3JtYWxpemVOYW1lKG5hbWUpIHtcbiAgaWYgKHR5cGVvZiBuYW1lICE9PSAnc3RyaW5nJykge1xuICAgIG5hbWUgPSBTdHJpbmcobmFtZSlcbiAgfVxuICBpZiAoL1teYS16MC05XFwtIyQlJicqKy5eX2B8fiFdL2kudGVzdChuYW1lKSB8fCBuYW1lID09PSAnJykge1xuICAgIHRocm93IG5ldyBUeXBlRXJyb3IoJ0ludmFsaWQgY2hhcmFjdGVyIGluIGhlYWRlciBmaWVsZCBuYW1lOiBcIicgKyBuYW1lICsgJ1wiJylcbiAgfVxuICByZXR1cm4gbmFtZS50b0xvd2VyQ2FzZSgpXG59XG5cbmZ1bmN0aW9uIG5vcm1hbGl6ZVZhbHVlKHZhbHVlKSB7XG4gIGlmICh0eXBlb2YgdmFsdWUgIT09ICdzdHJpbmcnKSB7XG4gICAgdmFsdWUgPSBTdHJpbmcodmFsdWUpXG4gIH1cbiAgcmV0dXJuIHZhbHVlXG59XG5cbi8vIEJ1aWxkIGEgZGVzdHJ1Y3RpdmUgaXRlcmF0b3IgZm9yIHRoZSB2YWx1ZSBsaXN0XG5mdW5jdGlvbiBpdGVyYXRvckZvcihpdGVtcykge1xuICB2YXIgaXRlcmF0b3IgPSB7XG4gICAgbmV4dDogZnVuY3Rpb24oKSB7XG4gICAgICB2YXIgdmFsdWUgPSBpdGVtcy5zaGlmdCgpXG4gICAgICByZXR1cm4ge2RvbmU6IHZhbHVlID09PSB1bmRlZmluZWQsIHZhbHVlOiB2YWx1ZX1cbiAgICB9XG4gIH1cblxuICBpZiAoc3VwcG9ydC5pdGVyYWJsZSkge1xuICAgIGl0ZXJhdG9yW1N5bWJvbC5pdGVyYXRvcl0gPSBmdW5jdGlvbigpIHtcbiAgICAgIHJldHVybiBpdGVyYXRvclxuICAgIH1cbiAgfVxuXG4gIHJldHVybiBpdGVyYXRvclxufVxuXG5leHBvcnQgZnVuY3Rpb24gSGVhZGVycyhoZWFkZXJzKSB7XG4gIHRoaXMubWFwID0ge31cblxuICBpZiAoaGVhZGVycyBpbnN0YW5jZW9mIEhlYWRlcnMpIHtcbiAgICBoZWFkZXJzLmZvckVhY2goZnVuY3Rpb24odmFsdWUsIG5hbWUpIHtcbiAgICAgIHRoaXMuYXBwZW5kKG5hbWUsIHZhbHVlKVxuICAgIH0sIHRoaXMpXG4gIH0gZWxzZSBpZiAoQXJyYXkuaXNBcnJheShoZWFkZXJzKSkge1xuICAgIGhlYWRlcnMuZm9yRWFjaChmdW5jdGlvbihoZWFkZXIpIHtcbiAgICAgIGlmIChoZWFkZXIubGVuZ3RoICE9IDIpIHtcbiAgICAgICAgdGhyb3cgbmV3IFR5cGVFcnJvcignSGVhZGVycyBjb25zdHJ1Y3RvcjogZXhwZWN0ZWQgbmFtZS92YWx1ZSBwYWlyIHRvIGJlIGxlbmd0aCAyLCBmb3VuZCcgKyBoZWFkZXIubGVuZ3RoKVxuICAgICAgfVxuICAgICAgdGhpcy5hcHBlbmQoaGVhZGVyWzBdLCBoZWFkZXJbMV0pXG4gICAgfSwgdGhpcylcbiAgfSBlbHNlIGlmIChoZWFkZXJzKSB7XG4gICAgT2JqZWN0LmdldE93blByb3BlcnR5TmFtZXMoaGVhZGVycykuZm9yRWFjaChmdW5jdGlvbihuYW1lKSB7XG4gICAgICB0aGlzLmFwcGVuZChuYW1lLCBoZWFkZXJzW25hbWVdKVxuICAgIH0sIHRoaXMpXG4gIH1cbn1cblxuSGVhZGVycy5wcm90b3R5cGUuYXBwZW5kID0gZnVuY3Rpb24obmFtZSwgdmFsdWUpIHtcbiAgbmFtZSA9IG5vcm1hbGl6ZU5hbWUobmFtZSlcbiAgdmFsdWUgPSBub3JtYWxpemVWYWx1ZSh2YWx1ZSlcbiAgdmFyIG9sZFZhbHVlID0gdGhpcy5tYXBbbmFtZV1cbiAgdGhpcy5tYXBbbmFtZV0gPSBvbGRWYWx1ZSA/IG9sZFZhbHVlICsgJywgJyArIHZhbHVlIDogdmFsdWVcbn1cblxuSGVhZGVycy5wcm90b3R5cGVbJ2RlbGV0ZSddID0gZnVuY3Rpb24obmFtZSkge1xuICBkZWxldGUgdGhpcy5tYXBbbm9ybWFsaXplTmFtZShuYW1lKV1cbn1cblxuSGVhZGVycy5wcm90b3R5cGUuZ2V0ID0gZnVuY3Rpb24obmFtZSkge1xuICBuYW1lID0gbm9ybWFsaXplTmFtZShuYW1lKVxuICByZXR1cm4gdGhpcy5oYXMobmFtZSkgPyB0aGlzLm1hcFtuYW1lXSA6IG51bGxcbn1cblxuSGVhZGVycy5wcm90b3R5cGUuaGFzID0gZnVuY3Rpb24obmFtZSkge1xuICByZXR1cm4gdGhpcy5tYXAuaGFzT3duUHJvcGVydHkobm9ybWFsaXplTmFtZShuYW1lKSlcbn1cblxuSGVhZGVycy5wcm90b3R5cGUuc2V0ID0gZnVuY3Rpb24obmFtZSwgdmFsdWUpIHtcbiAgdGhpcy5tYXBbbm9ybWFsaXplTmFtZShuYW1lKV0gPSBub3JtYWxpemVWYWx1ZSh2YWx1ZSlcbn1cblxuSGVhZGVycy5wcm90b3R5cGUuZm9yRWFjaCA9IGZ1bmN0aW9uKGNhbGxiYWNrLCB0aGlzQXJnKSB7XG4gIGZvciAodmFyIG5hbWUgaW4gdGhpcy5tYXApIHtcbiAgICBpZiAodGhpcy5tYXAuaGFzT3duUHJvcGVydHkobmFtZSkpIHtcbiAgICAgIGNhbGxiYWNrLmNhbGwodGhpc0FyZywgdGhpcy5tYXBbbmFtZV0sIG5hbWUsIHRoaXMpXG4gICAgfVxuICB9XG59XG5cbkhlYWRlcnMucHJvdG90eXBlLmtleXMgPSBmdW5jdGlvbigpIHtcbiAgdmFyIGl0ZW1zID0gW11cbiAgdGhpcy5mb3JFYWNoKGZ1bmN0aW9uKHZhbHVlLCBuYW1lKSB7XG4gICAgaXRlbXMucHVzaChuYW1lKVxuICB9KVxuICByZXR1cm4gaXRlcmF0b3JGb3IoaXRlbXMpXG59XG5cbkhlYWRlcnMucHJvdG90eXBlLnZhbHVlcyA9IGZ1bmN0aW9uKCkge1xuICB2YXIgaXRlbXMgPSBbXVxuICB0aGlzLmZvckVhY2goZnVuY3Rpb24odmFsdWUpIHtcbiAgICBpdGVtcy5wdXNoKHZhbHVlKVxuICB9KVxuICByZXR1cm4gaXRlcmF0b3JGb3IoaXRlbXMpXG59XG5cbkhlYWRlcnMucHJvdG90eXBlLmVudHJpZXMgPSBmdW5jdGlvbigpIHtcbiAgdmFyIGl0ZW1zID0gW11cbiAgdGhpcy5mb3JFYWNoKGZ1bmN0aW9uKHZhbHVlLCBuYW1lKSB7XG4gICAgaXRlbXMucHVzaChbbmFtZSwgdmFsdWVdKVxuICB9KVxuICByZXR1cm4gaXRlcmF0b3JGb3IoaXRlbXMpXG59XG5cbmlmIChzdXBwb3J0Lml0ZXJhYmxlKSB7XG4gIEhlYWRlcnMucHJvdG90eXBlW1N5bWJvbC5pdGVyYXRvcl0gPSBIZWFkZXJzLnByb3RvdHlwZS5lbnRyaWVzXG59XG5cbmZ1bmN0aW9uIGNvbnN1bWVkKGJvZHkpIHtcbiAgaWYgKGJvZHkuX25vQm9keSkgcmV0dXJuXG4gIGlmIChib2R5LmJvZHlVc2VkKSB7XG4gICAgcmV0dXJuIFByb21pc2UucmVqZWN0KG5ldyBUeXBlRXJyb3IoJ0FscmVhZHkgcmVhZCcpKVxuICB9XG4gIGJvZHkuYm9keVVzZWQgPSB0cnVlXG59XG5cbmZ1bmN0aW9uIGZpbGVSZWFkZXJSZWFkeShyZWFkZXIpIHtcbiAgcmV0dXJuIG5ldyBQcm9taXNlKGZ1bmN0aW9uKHJlc29sdmUsIHJlamVjdCkge1xuICAgIHJlYWRlci5vbmxvYWQgPSBmdW5jdGlvbigpIHtcbiAgICAgIHJlc29sdmUocmVhZGVyLnJlc3VsdClcbiAgICB9XG4gICAgcmVhZGVyLm9uZXJyb3IgPSBmdW5jdGlvbigpIHtcbiAgICAgIHJlamVjdChyZWFkZXIuZXJyb3IpXG4gICAgfVxuICB9KVxufVxuXG5mdW5jdGlvbiByZWFkQmxvYkFzQXJyYXlCdWZmZXIoYmxvYikge1xuICB2YXIgcmVhZGVyID0gbmV3IEZpbGVSZWFkZXIoKVxuICB2YXIgcHJvbWlzZSA9IGZpbGVSZWFkZXJSZWFkeShyZWFkZXIpXG4gIHJlYWRlci5yZWFkQXNBcnJheUJ1ZmZlcihibG9iKVxuICByZXR1cm4gcHJvbWlzZVxufVxuXG5mdW5jdGlvbiByZWFkQmxvYkFzVGV4dChibG9iKSB7XG4gIHZhciByZWFkZXIgPSBuZXcgRmlsZVJlYWRlcigpXG4gIHZhciBwcm9taXNlID0gZmlsZVJlYWRlclJlYWR5KHJlYWRlcilcbiAgdmFyIG1hdGNoID0gL2NoYXJzZXQ9KFtBLVphLXowLTlfLV0rKS8uZXhlYyhibG9iLnR5cGUpXG4gIHZhciBlbmNvZGluZyA9IG1hdGNoID8gbWF0Y2hbMV0gOiAndXRmLTgnXG4gIHJlYWRlci5yZWFkQXNUZXh0KGJsb2IsIGVuY29kaW5nKVxuICByZXR1cm4gcHJvbWlzZVxufVxuXG5mdW5jdGlvbiByZWFkQXJyYXlCdWZmZXJBc1RleHQoYnVmKSB7XG4gIHZhciB2aWV3ID0gbmV3IFVpbnQ4QXJyYXkoYnVmKVxuICB2YXIgY2hhcnMgPSBuZXcgQXJyYXkodmlldy5sZW5ndGgpXG5cbiAgZm9yICh2YXIgaSA9IDA7IGkgPCB2aWV3Lmxlbmd0aDsgaSsrKSB7XG4gICAgY2hhcnNbaV0gPSBTdHJpbmcuZnJvbUNoYXJDb2RlKHZpZXdbaV0pXG4gIH1cbiAgcmV0dXJuIGNoYXJzLmpvaW4oJycpXG59XG5cbmZ1bmN0aW9uIGJ1ZmZlckNsb25lKGJ1Zikge1xuICBpZiAoYnVmLnNsaWNlKSB7XG4gICAgcmV0dXJuIGJ1Zi5zbGljZSgwKVxuICB9IGVsc2Uge1xuICAgIHZhciB2aWV3ID0gbmV3IFVpbnQ4QXJyYXkoYnVmLmJ5dGVMZW5ndGgpXG4gICAgdmlldy5zZXQobmV3IFVpbnQ4QXJyYXkoYnVmKSlcbiAgICByZXR1cm4gdmlldy5idWZmZXJcbiAgfVxufVxuXG5mdW5jdGlvbiBCb2R5KCkge1xuICB0aGlzLmJvZHlVc2VkID0gZmFsc2VcblxuICB0aGlzLl9pbml0Qm9keSA9IGZ1bmN0aW9uKGJvZHkpIHtcbiAgICAvKlxuICAgICAgZmV0Y2gtbW9jayB3cmFwcyB0aGUgUmVzcG9uc2Ugb2JqZWN0IGluIGFuIEVTNiBQcm94eSB0b1xuICAgICAgcHJvdmlkZSB1c2VmdWwgdGVzdCBoYXJuZXNzIGZlYXR1cmVzIHN1Y2ggYXMgZmx1c2guIEhvd2V2ZXIsIG9uXG4gICAgICBFUzUgYnJvd3NlcnMgd2l0aG91dCBmZXRjaCBvciBQcm94eSBzdXBwb3J0IHBvbGx5ZmlsbHMgbXVzdCBiZSB1c2VkO1xuICAgICAgdGhlIHByb3h5LXBvbGx5ZmlsbCBpcyB1bmFibGUgdG8gcHJveHkgYW4gYXR0cmlidXRlIHVubGVzcyBpdCBleGlzdHNcbiAgICAgIG9uIHRoZSBvYmplY3QgYmVmb3JlIHRoZSBQcm94eSBpcyBjcmVhdGVkLiBUaGlzIGNoYW5nZSBlbnN1cmVzXG4gICAgICBSZXNwb25zZS5ib2R5VXNlZCBleGlzdHMgb24gdGhlIGluc3RhbmNlLCB3aGlsZSBtYWludGFpbmluZyB0aGVcbiAgICAgIHNlbWFudGljIG9mIHNldHRpbmcgUmVxdWVzdC5ib2R5VXNlZCBpbiB0aGUgY29uc3RydWN0b3IgYmVmb3JlXG4gICAgICBfaW5pdEJvZHkgaXMgY2FsbGVkLlxuICAgICovXG4gICAgLy8gZXNsaW50LWRpc2FibGUtbmV4dC1saW5lIG5vLXNlbGYtYXNzaWduXG4gICAgdGhpcy5ib2R5VXNlZCA9IHRoaXMuYm9keVVzZWRcbiAgICB0aGlzLl9ib2R5SW5pdCA9IGJvZHlcbiAgICBpZiAoIWJvZHkpIHtcbiAgICAgIHRoaXMuX25vQm9keSA9IHRydWU7XG4gICAgICB0aGlzLl9ib2R5VGV4dCA9ICcnXG4gICAgfSBlbHNlIGlmICh0eXBlb2YgYm9keSA9PT0gJ3N0cmluZycpIHtcbiAgICAgIHRoaXMuX2JvZHlUZXh0ID0gYm9keVxuICAgIH0gZWxzZSBpZiAoc3VwcG9ydC5ibG9iICYmIEJsb2IucHJvdG90eXBlLmlzUHJvdG90eXBlT2YoYm9keSkpIHtcbiAgICAgIHRoaXMuX2JvZHlCbG9iID0gYm9keVxuICAgIH0gZWxzZSBpZiAoc3VwcG9ydC5mb3JtRGF0YSAmJiBGb3JtRGF0YS5wcm90b3R5cGUuaXNQcm90b3R5cGVPZihib2R5KSkge1xuICAgICAgdGhpcy5fYm9keUZvcm1EYXRhID0gYm9keVxuICAgIH0gZWxzZSBpZiAoc3VwcG9ydC5zZWFyY2hQYXJhbXMgJiYgVVJMU2VhcmNoUGFyYW1zLnByb3RvdHlwZS5pc1Byb3RvdHlwZU9mKGJvZHkpKSB7XG4gICAgICB0aGlzLl9ib2R5VGV4dCA9IGJvZHkudG9TdHJpbmcoKVxuICAgIH0gZWxzZSBpZiAoc3VwcG9ydC5hcnJheUJ1ZmZlciAmJiBzdXBwb3J0LmJsb2IgJiYgaXNEYXRhVmlldyhib2R5KSkge1xuICAgICAgdGhpcy5fYm9keUFycmF5QnVmZmVyID0gYnVmZmVyQ2xvbmUoYm9keS5idWZmZXIpXG4gICAgICAvLyBJRSAxMC0xMSBjYW4ndCBoYW5kbGUgYSBEYXRhVmlldyBib2R5LlxuICAgICAgdGhpcy5fYm9keUluaXQgPSBuZXcgQmxvYihbdGhpcy5fYm9keUFycmF5QnVmZmVyXSlcbiAgICB9IGVsc2UgaWYgKHN1cHBvcnQuYXJyYXlCdWZmZXIgJiYgKEFycmF5QnVmZmVyLnByb3RvdHlwZS5pc1Byb3RvdHlwZU9mKGJvZHkpIHx8IGlzQXJyYXlCdWZmZXJWaWV3KGJvZHkpKSkge1xuICAgICAgdGhpcy5fYm9keUFycmF5QnVmZmVyID0gYnVmZmVyQ2xvbmUoYm9keSlcbiAgICB9IGVsc2Uge1xuICAgICAgdGhpcy5fYm9keVRleHQgPSBib2R5ID0gT2JqZWN0LnByb3RvdHlwZS50b1N0cmluZy5jYWxsKGJvZHkpXG4gICAgfVxuXG4gICAgaWYgKCF0aGlzLmhlYWRlcnMuZ2V0KCdjb250ZW50LXR5cGUnKSkge1xuICAgICAgaWYgKHR5cGVvZiBib2R5ID09PSAnc3RyaW5nJykge1xuICAgICAgICB0aGlzLmhlYWRlcnMuc2V0KCdjb250ZW50LXR5cGUnLCAndGV4dC9wbGFpbjtjaGFyc2V0PVVURi04JylcbiAgICAgIH0gZWxzZSBpZiAodGhpcy5fYm9keUJsb2IgJiYgdGhpcy5fYm9keUJsb2IudHlwZSkge1xuICAgICAgICB0aGlzLmhlYWRlcnMuc2V0KCdjb250ZW50LXR5cGUnLCB0aGlzLl9ib2R5QmxvYi50eXBlKVxuICAgICAgfSBlbHNlIGlmIChzdXBwb3J0LnNlYXJjaFBhcmFtcyAmJiBVUkxTZWFyY2hQYXJhbXMucHJvdG90eXBlLmlzUHJvdG90eXBlT2YoYm9keSkpIHtcbiAgICAgICAgdGhpcy5oZWFkZXJzLnNldCgnY29udGVudC10eXBlJywgJ2FwcGxpY2F0aW9uL3gtd3d3LWZvcm0tdXJsZW5jb2RlZDtjaGFyc2V0PVVURi04JylcbiAgICAgIH1cbiAgICB9XG4gIH1cblxuICBpZiAoc3VwcG9ydC5ibG9iKSB7XG4gICAgdGhpcy5ibG9iID0gZnVuY3Rpb24oKSB7XG4gICAgICB2YXIgcmVqZWN0ZWQgPSBjb25zdW1lZCh0aGlzKVxuICAgICAgaWYgKHJlamVjdGVkKSB7XG4gICAgICAgIHJldHVybiByZWplY3RlZFxuICAgICAgfVxuXG4gICAgICBpZiAodGhpcy5fYm9keUJsb2IpIHtcbiAgICAgICAgcmV0dXJuIFByb21pc2UucmVzb2x2ZSh0aGlzLl9ib2R5QmxvYilcbiAgICAgIH0gZWxzZSBpZiAodGhpcy5fYm9keUFycmF5QnVmZmVyKSB7XG4gICAgICAgIHJldHVybiBQcm9taXNlLnJlc29sdmUobmV3IEJsb2IoW3RoaXMuX2JvZHlBcnJheUJ1ZmZlcl0pKVxuICAgICAgfSBlbHNlIGlmICh0aGlzLl9ib2R5Rm9ybURhdGEpIHtcbiAgICAgICAgdGhyb3cgbmV3IEVycm9yKCdjb3VsZCBub3QgcmVhZCBGb3JtRGF0YSBib2R5IGFzIGJsb2InKVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgcmV0dXJuIFByb21pc2UucmVzb2x2ZShuZXcgQmxvYihbdGhpcy5fYm9keVRleHRdKSlcbiAgICAgIH1cbiAgICB9XG4gIH1cblxuICB0aGlzLmFycmF5QnVmZmVyID0gZnVuY3Rpb24oKSB7XG4gICAgaWYgKHRoaXMuX2JvZHlBcnJheUJ1ZmZlcikge1xuICAgICAgdmFyIGlzQ29uc3VtZWQgPSBjb25zdW1lZCh0aGlzKVxuICAgICAgaWYgKGlzQ29uc3VtZWQpIHtcbiAgICAgICAgcmV0dXJuIGlzQ29uc3VtZWRcbiAgICAgIH0gZWxzZSBpZiAoQXJyYXlCdWZmZXIuaXNWaWV3KHRoaXMuX2JvZHlBcnJheUJ1ZmZlcikpIHtcbiAgICAgICAgcmV0dXJuIFByb21pc2UucmVzb2x2ZShcbiAgICAgICAgICB0aGlzLl9ib2R5QXJyYXlCdWZmZXIuYnVmZmVyLnNsaWNlKFxuICAgICAgICAgICAgdGhpcy5fYm9keUFycmF5QnVmZmVyLmJ5dGVPZmZzZXQsXG4gICAgICAgICAgICB0aGlzLl9ib2R5QXJyYXlCdWZmZXIuYnl0ZU9mZnNldCArIHRoaXMuX2JvZHlBcnJheUJ1ZmZlci5ieXRlTGVuZ3RoXG4gICAgICAgICAgKVxuICAgICAgICApXG4gICAgICB9IGVsc2Uge1xuICAgICAgICByZXR1cm4gUHJvbWlzZS5yZXNvbHZlKHRoaXMuX2JvZHlBcnJheUJ1ZmZlcilcbiAgICAgIH1cbiAgICB9IGVsc2UgaWYgKHN1cHBvcnQuYmxvYikge1xuICAgICAgcmV0dXJuIHRoaXMuYmxvYigpLnRoZW4ocmVhZEJsb2JBc0FycmF5QnVmZmVyKVxuICAgIH0gZWxzZSB7XG4gICAgICB0aHJvdyBuZXcgRXJyb3IoJ2NvdWxkIG5vdCByZWFkIGFzIEFycmF5QnVmZmVyJylcbiAgICB9XG4gIH1cblxuICB0aGlzLnRleHQgPSBmdW5jdGlvbigpIHtcbiAgICB2YXIgcmVqZWN0ZWQgPSBjb25zdW1lZCh0aGlzKVxuICAgIGlmIChyZWplY3RlZCkge1xuICAgICAgcmV0dXJuIHJlamVjdGVkXG4gICAgfVxuXG4gICAgaWYgKHRoaXMuX2JvZHlCbG9iKSB7XG4gICAgICByZXR1cm4gcmVhZEJsb2JBc1RleHQodGhpcy5fYm9keUJsb2IpXG4gICAgfSBlbHNlIGlmICh0aGlzLl9ib2R5QXJyYXlCdWZmZXIpIHtcbiAgICAgIHJldHVybiBQcm9taXNlLnJlc29sdmUocmVhZEFycmF5QnVmZmVyQXNUZXh0KHRoaXMuX2JvZHlBcnJheUJ1ZmZlcikpXG4gICAgfSBlbHNlIGlmICh0aGlzLl9ib2R5Rm9ybURhdGEpIHtcbiAgICAgIHRocm93IG5ldyBFcnJvcignY291bGQgbm90IHJlYWQgRm9ybURhdGEgYm9keSBhcyB0ZXh0JylcbiAgICB9IGVsc2Uge1xuICAgICAgcmV0dXJuIFByb21pc2UucmVzb2x2ZSh0aGlzLl9ib2R5VGV4dClcbiAgICB9XG4gIH1cblxuICBpZiAoc3VwcG9ydC5mb3JtRGF0YSkge1xuICAgIHRoaXMuZm9ybURhdGEgPSBmdW5jdGlvbigpIHtcbiAgICAgIHJldHVybiB0aGlzLnRleHQoKS50aGVuKGRlY29kZSlcbiAgICB9XG4gIH1cblxuICB0aGlzLmpzb24gPSBmdW5jdGlvbigpIHtcbiAgICByZXR1cm4gdGhpcy50ZXh0KCkudGhlbihKU09OLnBhcnNlKVxuICB9XG5cbiAgcmV0dXJuIHRoaXNcbn1cblxuLy8gSFRUUCBtZXRob2RzIHdob3NlIGNhcGl0YWxpemF0aW9uIHNob3VsZCBiZSBub3JtYWxpemVkXG52YXIgbWV0aG9kcyA9IFsnQ09OTkVDVCcsICdERUxFVEUnLCAnR0VUJywgJ0hFQUQnLCAnT1BUSU9OUycsICdQQVRDSCcsICdQT1NUJywgJ1BVVCcsICdUUkFDRSddXG5cbmZ1bmN0aW9uIG5vcm1hbGl6ZU1ldGhvZChtZXRob2QpIHtcbiAgdmFyIHVwY2FzZWQgPSBtZXRob2QudG9VcHBlckNhc2UoKVxuICByZXR1cm4gbWV0aG9kcy5pbmRleE9mKHVwY2FzZWQpID4gLTEgPyB1cGNhc2VkIDogbWV0aG9kXG59XG5cbmV4cG9ydCBmdW5jdGlvbiBSZXF1ZXN0KGlucHV0LCBvcHRpb25zKSB7XG4gIGlmICghKHRoaXMgaW5zdGFuY2VvZiBSZXF1ZXN0KSkge1xuICAgIHRocm93IG5ldyBUeXBlRXJyb3IoJ1BsZWFzZSB1c2UgdGhlIFwibmV3XCIgb3BlcmF0b3IsIHRoaXMgRE9NIG9iamVjdCBjb25zdHJ1Y3RvciBjYW5ub3QgYmUgY2FsbGVkIGFzIGEgZnVuY3Rpb24uJylcbiAgfVxuXG4gIG9wdGlvbnMgPSBvcHRpb25zIHx8IHt9XG4gIHZhciBib2R5ID0gb3B0aW9ucy5ib2R5XG5cbiAgaWYgKGlucHV0IGluc3RhbmNlb2YgUmVxdWVzdCkge1xuICAgIGlmIChpbnB1dC5ib2R5VXNlZCkge1xuICAgICAgdGhyb3cgbmV3IFR5cGVFcnJvcignQWxyZWFkeSByZWFkJylcbiAgICB9XG4gICAgdGhpcy51cmwgPSBpbnB1dC51cmxcbiAgICB0aGlzLmNyZWRlbnRpYWxzID0gaW5wdXQuY3JlZGVudGlhbHNcbiAgICBpZiAoIW9wdGlvbnMuaGVhZGVycykge1xuICAgICAgdGhpcy5oZWFkZXJzID0gbmV3IEhlYWRlcnMoaW5wdXQuaGVhZGVycylcbiAgICB9XG4gICAgdGhpcy5tZXRob2QgPSBpbnB1dC5tZXRob2RcbiAgICB0aGlzLm1vZGUgPSBpbnB1dC5tb2RlXG4gICAgdGhpcy5zaWduYWwgPSBpbnB1dC5zaWduYWxcbiAgICBpZiAoIWJvZHkgJiYgaW5wdXQuX2JvZHlJbml0ICE9IG51bGwpIHtcbiAgICAgIGJvZHkgPSBpbnB1dC5fYm9keUluaXRcbiAgICAgIGlucHV0LmJvZHlVc2VkID0gdHJ1ZVxuICAgIH1cbiAgfSBlbHNlIHtcbiAgICB0aGlzLnVybCA9IFN0cmluZyhpbnB1dClcbiAgfVxuXG4gIHRoaXMuY3JlZGVudGlhbHMgPSBvcHRpb25zLmNyZWRlbnRpYWxzIHx8IHRoaXMuY3JlZGVudGlhbHMgfHwgJ3NhbWUtb3JpZ2luJ1xuICBpZiAob3B0aW9ucy5oZWFkZXJzIHx8ICF0aGlzLmhlYWRlcnMpIHtcbiAgICB0aGlzLmhlYWRlcnMgPSBuZXcgSGVhZGVycyhvcHRpb25zLmhlYWRlcnMpXG4gIH1cbiAgdGhpcy5tZXRob2QgPSBub3JtYWxpemVNZXRob2Qob3B0aW9ucy5tZXRob2QgfHwgdGhpcy5tZXRob2QgfHwgJ0dFVCcpXG4gIHRoaXMubW9kZSA9IG9wdGlvbnMubW9kZSB8fCB0aGlzLm1vZGUgfHwgbnVsbFxuICB0aGlzLnNpZ25hbCA9IG9wdGlvbnMuc2lnbmFsIHx8IHRoaXMuc2lnbmFsIHx8IChmdW5jdGlvbiAoKSB7XG4gICAgaWYgKCdBYm9ydENvbnRyb2xsZXInIGluIGcpIHtcbiAgICAgIHZhciBjdHJsID0gbmV3IEFib3J0Q29udHJvbGxlcigpO1xuICAgICAgcmV0dXJuIGN0cmwuc2lnbmFsO1xuICAgIH1cbiAgfSgpKTtcbiAgdGhpcy5yZWZlcnJlciA9IG51bGxcblxuICBpZiAoKHRoaXMubWV0aG9kID09PSAnR0VUJyB8fCB0aGlzLm1ldGhvZCA9PT0gJ0hFQUQnKSAmJiBib2R5KSB7XG4gICAgdGhyb3cgbmV3IFR5cGVFcnJvcignQm9keSBub3QgYWxsb3dlZCBmb3IgR0VUIG9yIEhFQUQgcmVxdWVzdHMnKVxuICB9XG4gIHRoaXMuX2luaXRCb2R5KGJvZHkpXG5cbiAgaWYgKHRoaXMubWV0aG9kID09PSAnR0VUJyB8fCB0aGlzLm1ldGhvZCA9PT0gJ0hFQUQnKSB7XG4gICAgaWYgKG9wdGlvbnMuY2FjaGUgPT09ICduby1zdG9yZScgfHwgb3B0aW9ucy5jYWNoZSA9PT0gJ25vLWNhY2hlJykge1xuICAgICAgLy8gU2VhcmNoIGZvciBhICdfJyBwYXJhbWV0ZXIgaW4gdGhlIHF1ZXJ5IHN0cmluZ1xuICAgICAgdmFyIHJlUGFyYW1TZWFyY2ggPSAvKFs/Jl0pXz1bXiZdKi9cbiAgICAgIGlmIChyZVBhcmFtU2VhcmNoLnRlc3QodGhpcy51cmwpKSB7XG4gICAgICAgIC8vIElmIGl0IGFscmVhZHkgZXhpc3RzIHRoZW4gc2V0IHRoZSB2YWx1ZSB3aXRoIHRoZSBjdXJyZW50IHRpbWVcbiAgICAgICAgdGhpcy51cmwgPSB0aGlzLnVybC5yZXBsYWNlKHJlUGFyYW1TZWFyY2gsICckMV89JyArIG5ldyBEYXRlKCkuZ2V0VGltZSgpKVxuICAgICAgfSBlbHNlIHtcbiAgICAgICAgLy8gT3RoZXJ3aXNlIGFkZCBhIG5ldyAnXycgcGFyYW1ldGVyIHRvIHRoZSBlbmQgd2l0aCB0aGUgY3VycmVudCB0aW1lXG4gICAgICAgIHZhciByZVF1ZXJ5U3RyaW5nID0gL1xcPy9cbiAgICAgICAgdGhpcy51cmwgKz0gKHJlUXVlcnlTdHJpbmcudGVzdCh0aGlzLnVybCkgPyAnJicgOiAnPycpICsgJ189JyArIG5ldyBEYXRlKCkuZ2V0VGltZSgpXG4gICAgICB9XG4gICAgfVxuICB9XG59XG5cblJlcXVlc3QucHJvdG90eXBlLmNsb25lID0gZnVuY3Rpb24oKSB7XG4gIHJldHVybiBuZXcgUmVxdWVzdCh0aGlzLCB7Ym9keTogdGhpcy5fYm9keUluaXR9KVxufVxuXG5mdW5jdGlvbiBkZWNvZGUoYm9keSkge1xuICB2YXIgZm9ybSA9IG5ldyBGb3JtRGF0YSgpXG4gIGJvZHlcbiAgICAudHJpbSgpXG4gICAgLnNwbGl0KCcmJylcbiAgICAuZm9yRWFjaChmdW5jdGlvbihieXRlcykge1xuICAgICAgaWYgKGJ5dGVzKSB7XG4gICAgICAgIHZhciBzcGxpdCA9IGJ5dGVzLnNwbGl0KCc9JylcbiAgICAgICAgdmFyIG5hbWUgPSBzcGxpdC5zaGlmdCgpLnJlcGxhY2UoL1xcKy9nLCAnICcpXG4gICAgICAgIHZhciB2YWx1ZSA9IHNwbGl0LmpvaW4oJz0nKS5yZXBsYWNlKC9cXCsvZywgJyAnKVxuICAgICAgICBmb3JtLmFwcGVuZChkZWNvZGVVUklDb21wb25lbnQobmFtZSksIGRlY29kZVVSSUNvbXBvbmVudCh2YWx1ZSkpXG4gICAgICB9XG4gICAgfSlcbiAgcmV0dXJuIGZvcm1cbn1cblxuZnVuY3Rpb24gcGFyc2VIZWFkZXJzKHJhd0hlYWRlcnMpIHtcbiAgdmFyIGhlYWRlcnMgPSBuZXcgSGVhZGVycygpXG4gIC8vIFJlcGxhY2UgaW5zdGFuY2VzIG9mIFxcclxcbiBhbmQgXFxuIGZvbGxvd2VkIGJ5IGF0IGxlYXN0IG9uZSBzcGFjZSBvciBob3Jpem9udGFsIHRhYiB3aXRoIGEgc3BhY2VcbiAgLy8gaHR0cHM6Ly90b29scy5pZXRmLm9yZy9odG1sL3JmYzcyMzAjc2VjdGlvbi0zLjJcbiAgdmFyIHByZVByb2Nlc3NlZEhlYWRlcnMgPSByYXdIZWFkZXJzLnJlcGxhY2UoL1xccj9cXG5bXFx0IF0rL2csICcgJylcbiAgLy8gQXZvaWRpbmcgc3BsaXQgdmlhIHJlZ2V4IHRvIHdvcmsgYXJvdW5kIGEgY29tbW9uIElFMTEgYnVnIHdpdGggdGhlIGNvcmUtanMgMy42LjAgcmVnZXggcG9seWZpbGxcbiAgLy8gaHR0cHM6Ly9naXRodWIuY29tL2dpdGh1Yi9mZXRjaC9pc3N1ZXMvNzQ4XG4gIC8vIGh0dHBzOi8vZ2l0aHViLmNvbS96bG9pcm9jay9jb3JlLWpzL2lzc3Vlcy83NTFcbiAgcHJlUHJvY2Vzc2VkSGVhZGVyc1xuICAgIC5zcGxpdCgnXFxyJylcbiAgICAubWFwKGZ1bmN0aW9uKGhlYWRlcikge1xuICAgICAgcmV0dXJuIGhlYWRlci5pbmRleE9mKCdcXG4nKSA9PT0gMCA/IGhlYWRlci5zdWJzdHIoMSwgaGVhZGVyLmxlbmd0aCkgOiBoZWFkZXJcbiAgICB9KVxuICAgIC5mb3JFYWNoKGZ1bmN0aW9uKGxpbmUpIHtcbiAgICAgIHZhciBwYXJ0cyA9IGxpbmUuc3BsaXQoJzonKVxuICAgICAgdmFyIGtleSA9IHBhcnRzLnNoaWZ0KCkudHJpbSgpXG4gICAgICBpZiAoa2V5KSB7XG4gICAgICAgIHZhciB2YWx1ZSA9IHBhcnRzLmpvaW4oJzonKS50cmltKClcbiAgICAgICAgdHJ5IHtcbiAgICAgICAgICBoZWFkZXJzLmFwcGVuZChrZXksIHZhbHVlKVxuICAgICAgICB9IGNhdGNoIChlcnJvcikge1xuICAgICAgICAgIGNvbnNvbGUud2FybignUmVzcG9uc2UgJyArIGVycm9yLm1lc3NhZ2UpXG4gICAgICAgIH1cbiAgICAgIH1cbiAgICB9KVxuICByZXR1cm4gaGVhZGVyc1xufVxuXG5Cb2R5LmNhbGwoUmVxdWVzdC5wcm90b3R5cGUpXG5cbmV4cG9ydCBmdW5jdGlvbiBSZXNwb25zZShib2R5SW5pdCwgb3B0aW9ucykge1xuICBpZiAoISh0aGlzIGluc3RhbmNlb2YgUmVzcG9uc2UpKSB7XG4gICAgdGhyb3cgbmV3IFR5cGVFcnJvcignUGxlYXNlIHVzZSB0aGUgXCJuZXdcIiBvcGVyYXRvciwgdGhpcyBET00gb2JqZWN0IGNvbnN0cnVjdG9yIGNhbm5vdCBiZSBjYWxsZWQgYXMgYSBmdW5jdGlvbi4nKVxuICB9XG4gIGlmICghb3B0aW9ucykge1xuICAgIG9wdGlvbnMgPSB7fVxuICB9XG5cbiAgdGhpcy50eXBlID0gJ2RlZmF1bHQnXG4gIHRoaXMuc3RhdHVzID0gb3B0aW9ucy5zdGF0dXMgPT09IHVuZGVmaW5lZCA/IDIwMCA6IG9wdGlvbnMuc3RhdHVzXG4gIGlmICh0aGlzLnN0YXR1cyA8IDIwMCB8fCB0aGlzLnN0YXR1cyA+IDU5OSkge1xuICAgIHRocm93IG5ldyBSYW5nZUVycm9yKFwiRmFpbGVkIHRvIGNvbnN0cnVjdCAnUmVzcG9uc2UnOiBUaGUgc3RhdHVzIHByb3ZpZGVkICgwKSBpcyBvdXRzaWRlIHRoZSByYW5nZSBbMjAwLCA1OTldLlwiKVxuICB9XG4gIHRoaXMub2sgPSB0aGlzLnN0YXR1cyA+PSAyMDAgJiYgdGhpcy5zdGF0dXMgPCAzMDBcbiAgdGhpcy5zdGF0dXNUZXh0ID0gb3B0aW9ucy5zdGF0dXNUZXh0ID09PSB1bmRlZmluZWQgPyAnJyA6ICcnICsgb3B0aW9ucy5zdGF0dXNUZXh0XG4gIHRoaXMuaGVhZGVycyA9IG5ldyBIZWFkZXJzKG9wdGlvbnMuaGVhZGVycylcbiAgdGhpcy51cmwgPSBvcHRpb25zLnVybCB8fCAnJ1xuICB0aGlzLl9pbml0Qm9keShib2R5SW5pdClcbn1cblxuQm9keS5jYWxsKFJlc3BvbnNlLnByb3RvdHlwZSlcblxuUmVzcG9uc2UucHJvdG90eXBlLmNsb25lID0gZnVuY3Rpb24oKSB7XG4gIHJldHVybiBuZXcgUmVzcG9uc2UodGhpcy5fYm9keUluaXQsIHtcbiAgICBzdGF0dXM6IHRoaXMuc3RhdHVzLFxuICAgIHN0YXR1c1RleHQ6IHRoaXMuc3RhdHVzVGV4dCxcbiAgICBoZWFkZXJzOiBuZXcgSGVhZGVycyh0aGlzLmhlYWRlcnMpLFxuICAgIHVybDogdGhpcy51cmxcbiAgfSlcbn1cblxuUmVzcG9uc2UuZXJyb3IgPSBmdW5jdGlvbigpIHtcbiAgdmFyIHJlc3BvbnNlID0gbmV3IFJlc3BvbnNlKG51bGwsIHtzdGF0dXM6IDIwMCwgc3RhdHVzVGV4dDogJyd9KVxuICByZXNwb25zZS5vayA9IGZhbHNlXG4gIHJlc3BvbnNlLnN0YXR1cyA9IDBcbiAgcmVzcG9uc2UudHlwZSA9ICdlcnJvcidcbiAgcmV0dXJuIHJlc3BvbnNlXG59XG5cbnZhciByZWRpcmVjdFN0YXR1c2VzID0gWzMwMSwgMzAyLCAzMDMsIDMwNywgMzA4XVxuXG5SZXNwb25zZS5yZWRpcmVjdCA9IGZ1bmN0aW9uKHVybCwgc3RhdHVzKSB7XG4gIGlmIChyZWRpcmVjdFN0YXR1c2VzLmluZGV4T2Yoc3RhdHVzKSA9PT0gLTEpIHtcbiAgICB0aHJvdyBuZXcgUmFuZ2VFcnJvcignSW52YWxpZCBzdGF0dXMgY29kZScpXG4gIH1cblxuICByZXR1cm4gbmV3IFJlc3BvbnNlKG51bGwsIHtzdGF0dXM6IHN0YXR1cywgaGVhZGVyczoge2xvY2F0aW9uOiB1cmx9fSlcbn1cblxuZXhwb3J0IHZhciBET01FeGNlcHRpb24gPSBnLkRPTUV4Y2VwdGlvblxudHJ5IHtcbiAgbmV3IERPTUV4Y2VwdGlvbigpXG59IGNhdGNoIChlcnIpIHtcbiAgRE9NRXhjZXB0aW9uID0gZnVuY3Rpb24obWVzc2FnZSwgbmFtZSkge1xuICAgIHRoaXMubWVzc2FnZSA9IG1lc3NhZ2VcbiAgICB0aGlzLm5hbWUgPSBuYW1lXG4gICAgdmFyIGVycm9yID0gRXJyb3IobWVzc2FnZSlcbiAgICB0aGlzLnN0YWNrID0gZXJyb3Iuc3RhY2tcbiAgfVxuICBET01FeGNlcHRpb24ucHJvdG90eXBlID0gT2JqZWN0LmNyZWF0ZShFcnJvci5wcm90b3R5cGUpXG4gIERPTUV4Y2VwdGlvbi5wcm90b3R5cGUuY29uc3RydWN0b3IgPSBET01FeGNlcHRpb25cbn1cblxuZXhwb3J0IGZ1bmN0aW9uIGZldGNoKGlucHV0LCBpbml0KSB7XG4gIHJldHVybiBuZXcgUHJvbWlzZShmdW5jdGlvbihyZXNvbHZlLCByZWplY3QpIHtcbiAgICB2YXIgcmVxdWVzdCA9IG5ldyBSZXF1ZXN0KGlucHV0LCBpbml0KVxuXG4gICAgaWYgKHJlcXVlc3Quc2lnbmFsICYmIHJlcXVlc3Quc2lnbmFsLmFib3J0ZWQpIHtcbiAgICAgIHJldHVybiByZWplY3QobmV3IERPTUV4Y2VwdGlvbignQWJvcnRlZCcsICdBYm9ydEVycm9yJykpXG4gICAgfVxuXG4gICAgdmFyIHhociA9IG5ldyBYTUxIdHRwUmVxdWVzdCgpXG5cbiAgICBmdW5jdGlvbiBhYm9ydFhocigpIHtcbiAgICAgIHhoci5hYm9ydCgpXG4gICAgfVxuXG4gICAgeGhyLm9ubG9hZCA9IGZ1bmN0aW9uKCkge1xuICAgICAgdmFyIG9wdGlvbnMgPSB7XG4gICAgICAgIHN0YXR1c1RleHQ6IHhoci5zdGF0dXNUZXh0LFxuICAgICAgICBoZWFkZXJzOiBwYXJzZUhlYWRlcnMoeGhyLmdldEFsbFJlc3BvbnNlSGVhZGVycygpIHx8ICcnKVxuICAgICAgfVxuICAgICAgLy8gVGhpcyBjaGVjayBpZiBzcGVjaWZpY2FsbHkgZm9yIHdoZW4gYSB1c2VyIGZldGNoZXMgYSBmaWxlIGxvY2FsbHkgZnJvbSB0aGUgZmlsZSBzeXN0ZW1cbiAgICAgIC8vIE9ubHkgaWYgdGhlIHN0YXR1cyBpcyBvdXQgb2YgYSBub3JtYWwgcmFuZ2VcbiAgICAgIGlmIChyZXF1ZXN0LnVybC5pbmRleE9mKCdmaWxlOi8vJykgPT09IDAgJiYgKHhoci5zdGF0dXMgPCAyMDAgfHwgeGhyLnN0YXR1cyA+IDU5OSkpIHtcbiAgICAgICAgb3B0aW9ucy5zdGF0dXMgPSAyMDA7XG4gICAgICB9IGVsc2Uge1xuICAgICAgICBvcHRpb25zLnN0YXR1cyA9IHhoci5zdGF0dXM7XG4gICAgICB9XG4gICAgICBvcHRpb25zLnVybCA9ICdyZXNwb25zZVVSTCcgaW4geGhyID8geGhyLnJlc3BvbnNlVVJMIDogb3B0aW9ucy5oZWFkZXJzLmdldCgnWC1SZXF1ZXN0LVVSTCcpXG4gICAgICB2YXIgYm9keSA9ICdyZXNwb25zZScgaW4geGhyID8geGhyLnJlc3BvbnNlIDogeGhyLnJlc3BvbnNlVGV4dFxuICAgICAgc2V0VGltZW91dChmdW5jdGlvbigpIHtcbiAgICAgICAgcmVzb2x2ZShuZXcgUmVzcG9uc2UoYm9keSwgb3B0aW9ucykpXG4gICAgICB9LCAwKVxuICAgIH1cblxuICAgIHhoci5vbmVycm9yID0gZnVuY3Rpb24oKSB7XG4gICAgICBzZXRUaW1lb3V0KGZ1bmN0aW9uKCkge1xuICAgICAgICByZWplY3QobmV3IFR5cGVFcnJvcignTmV0d29yayByZXF1ZXN0IGZhaWxlZCcpKVxuICAgICAgfSwgMClcbiAgICB9XG5cbiAgICB4aHIub250aW1lb3V0ID0gZnVuY3Rpb24oKSB7XG4gICAgICBzZXRUaW1lb3V0KGZ1bmN0aW9uKCkge1xuICAgICAgICByZWplY3QobmV3IFR5cGVFcnJvcignTmV0d29yayByZXF1ZXN0IHRpbWVkIG91dCcpKVxuICAgICAgfSwgMClcbiAgICB9XG5cbiAgICB4aHIub25hYm9ydCA9IGZ1bmN0aW9uKCkge1xuICAgICAgc2V0VGltZW91dChmdW5jdGlvbigpIHtcbiAgICAgICAgcmVqZWN0KG5ldyBET01FeGNlcHRpb24oJ0Fib3J0ZWQnLCAnQWJvcnRFcnJvcicpKVxuICAgICAgfSwgMClcbiAgICB9XG5cbiAgICBmdW5jdGlvbiBmaXhVcmwodXJsKSB7XG4gICAgICB0cnkge1xuICAgICAgICByZXR1cm4gdXJsID09PSAnJyAmJiBnLmxvY2F0aW9uLmhyZWYgPyBnLmxvY2F0aW9uLmhyZWYgOiB1cmxcbiAgICAgIH0gY2F0Y2ggKGUpIHtcbiAgICAgICAgcmV0dXJuIHVybFxuICAgICAgfVxuICAgIH1cblxuICAgIHhoci5vcGVuKHJlcXVlc3QubWV0aG9kLCBmaXhVcmwocmVxdWVzdC51cmwpLCB0cnVlKVxuXG4gICAgaWYgKHJlcXVlc3QuY3JlZGVudGlhbHMgPT09ICdpbmNsdWRlJykge1xuICAgICAgeGhyLndpdGhDcmVkZW50aWFscyA9IHRydWVcbiAgICB9IGVsc2UgaWYgKHJlcXVlc3QuY3JlZGVudGlhbHMgPT09ICdvbWl0Jykge1xuICAgICAgeGhyLndpdGhDcmVkZW50aWFscyA9IGZhbHNlXG4gICAgfVxuXG4gICAgaWYgKCdyZXNwb25zZVR5cGUnIGluIHhocikge1xuICAgICAgaWYgKHN1cHBvcnQuYmxvYikge1xuICAgICAgICB4aHIucmVzcG9uc2VUeXBlID0gJ2Jsb2InXG4gICAgICB9IGVsc2UgaWYgKFxuICAgICAgICBzdXBwb3J0LmFycmF5QnVmZmVyXG4gICAgICApIHtcbiAgICAgICAgeGhyLnJlc3BvbnNlVHlwZSA9ICdhcnJheWJ1ZmZlcidcbiAgICAgIH1cbiAgICB9XG5cbiAgICBpZiAoaW5pdCAmJiB0eXBlb2YgaW5pdC5oZWFkZXJzID09PSAnb2JqZWN0JyAmJiAhKGluaXQuaGVhZGVycyBpbnN0YW5jZW9mIEhlYWRlcnMgfHwgKGcuSGVhZGVycyAmJiBpbml0LmhlYWRlcnMgaW5zdGFuY2VvZiBnLkhlYWRlcnMpKSkge1xuICAgICAgdmFyIG5hbWVzID0gW107XG4gICAgICBPYmplY3QuZ2V0T3duUHJvcGVydHlOYW1lcyhpbml0LmhlYWRlcnMpLmZvckVhY2goZnVuY3Rpb24obmFtZSkge1xuICAgICAgICBuYW1lcy5wdXNoKG5vcm1hbGl6ZU5hbWUobmFtZSkpXG4gICAgICAgIHhoci5zZXRSZXF1ZXN0SGVhZGVyKG5hbWUsIG5vcm1hbGl6ZVZhbHVlKGluaXQuaGVhZGVyc1tuYW1lXSkpXG4gICAgICB9KVxuICAgICAgcmVxdWVzdC5oZWFkZXJzLmZvckVhY2goZnVuY3Rpb24odmFsdWUsIG5hbWUpIHtcbiAgICAgICAgaWYgKG5hbWVzLmluZGV4T2YobmFtZSkgPT09IC0xKSB7XG4gICAgICAgICAgeGhyLnNldFJlcXVlc3RIZWFkZXIobmFtZSwgdmFsdWUpXG4gICAgICAgIH1cbiAgICAgIH0pXG4gICAgfSBlbHNlIHtcbiAgICAgIHJlcXVlc3QuaGVhZGVycy5mb3JFYWNoKGZ1bmN0aW9uKHZhbHVlLCBuYW1lKSB7XG4gICAgICAgIHhoci5zZXRSZXF1ZXN0SGVhZGVyKG5hbWUsIHZhbHVlKVxuICAgICAgfSlcbiAgICB9XG5cbiAgICBpZiAocmVxdWVzdC5zaWduYWwpIHtcbiAgICAgIHJlcXVlc3Quc2lnbmFsLmFkZEV2ZW50TGlzdGVuZXIoJ2Fib3J0JywgYWJvcnRYaHIpXG5cbiAgICAgIHhoci5vbnJlYWR5c3RhdGVjaGFuZ2UgPSBmdW5jdGlvbigpIHtcbiAgICAgICAgLy8gRE9ORSAoc3VjY2VzcyBvciBmYWlsdXJlKVxuICAgICAgICBpZiAoeGhyLnJlYWR5U3RhdGUgPT09IDQpIHtcbiAgICAgICAgICByZXF1ZXN0LnNpZ25hbC5yZW1vdmVFdmVudExpc3RlbmVyKCdhYm9ydCcsIGFib3J0WGhyKVxuICAgICAgICB9XG4gICAgICB9XG4gICAgfVxuXG4gICAgeGhyLnNlbmQodHlwZW9mIHJlcXVlc3QuX2JvZHlJbml0ID09PSAndW5kZWZpbmVkJyA/IG51bGwgOiByZXF1ZXN0Ll9ib2R5SW5pdClcbiAgfSlcbn1cblxuZmV0Y2gucG9seWZpbGwgPSB0cnVlXG5cbmlmICghZy5mZXRjaCkge1xuICBnLmZldGNoID0gZmV0Y2hcbiAgZy5IZWFkZXJzID0gSGVhZGVyc1xuICBnLlJlcXVlc3QgPSBSZXF1ZXN0XG4gIGcuUmVzcG9uc2UgPSBSZXNwb25zZVxufVxuIiwiJ3VzZSBzdHJpY3QnO1xuXG5PYmplY3QuZGVmaW5lUHJvcGVydHkoZXhwb3J0cywgJ19fZXNNb2R1bGUnLCB7IHZhbHVlOiB0cnVlIH0pO1xuXG5yZXF1aXJlKCd3aGF0d2ctZmV0Y2gnKTtcblxuY29uc3QgZGVmYXVsdFBvcnQgPSBcIjExNDM0XCI7XG5jb25zdCBkZWZhdWx0SG9zdCA9IGBodHRwOi8vMTI3LjAuMC4xOiR7ZGVmYXVsdFBvcnR9YDtcblxuY29uc3QgdmVyc2lvbiA9IFwiMC42LjNcIjtcblxudmFyIF9fZGVmUHJvcCQxID0gT2JqZWN0LmRlZmluZVByb3BlcnR5O1xudmFyIF9fZGVmTm9ybWFsUHJvcCQxID0gKG9iaiwga2V5LCB2YWx1ZSkgPT4ga2V5IGluIG9iaiA/IF9fZGVmUHJvcCQxKG9iaiwga2V5LCB7IGVudW1lcmFibGU6IHRydWUsIGNvbmZpZ3VyYWJsZTogdHJ1ZSwgd3JpdGFibGU6IHRydWUsIHZhbHVlIH0pIDogb2JqW2tleV0gPSB2YWx1ZTtcbnZhciBfX3B1YmxpY0ZpZWxkJDEgPSAob2JqLCBrZXksIHZhbHVlKSA9PiB7XG4gIF9fZGVmTm9ybWFsUHJvcCQxKG9iaiwgdHlwZW9mIGtleSAhPT0gXCJzeW1ib2xcIiA/IGtleSArIFwiXCIgOiBrZXksIHZhbHVlKTtcbiAgcmV0dXJuIHZhbHVlO1xufTtcbmNsYXNzIFJlc3BvbnNlRXJyb3IgZXh0ZW5kcyBFcnJvciB7XG4gIGNvbnN0cnVjdG9yKGVycm9yLCBzdGF0dXNfY29kZSkge1xuICAgIHN1cGVyKGVycm9yKTtcbiAgICB0aGlzLmVycm9yID0gZXJyb3I7XG4gICAgdGhpcy5zdGF0dXNfY29kZSA9IHN0YXR1c19jb2RlO1xuICAgIHRoaXMubmFtZSA9IFwiUmVzcG9uc2VFcnJvclwiO1xuICAgIGlmIChFcnJvci5jYXB0dXJlU3RhY2tUcmFjZSkge1xuICAgICAgRXJyb3IuY2FwdHVyZVN0YWNrVHJhY2UodGhpcywgUmVzcG9uc2VFcnJvcik7XG4gICAgfVxuICB9XG59XG5jbGFzcyBBYm9ydGFibGVBc3luY0l0ZXJhdG9yIHtcbiAgY29uc3RydWN0b3IoYWJvcnRDb250cm9sbGVyLCBpdHIsIGRvbmVDYWxsYmFjaykge1xuICAgIF9fcHVibGljRmllbGQkMSh0aGlzLCBcImFib3J0Q29udHJvbGxlclwiKTtcbiAgICBfX3B1YmxpY0ZpZWxkJDEodGhpcywgXCJpdHJcIik7XG4gICAgX19wdWJsaWNGaWVsZCQxKHRoaXMsIFwiZG9uZUNhbGxiYWNrXCIpO1xuICAgIHRoaXMuYWJvcnRDb250cm9sbGVyID0gYWJvcnRDb250cm9sbGVyO1xuICAgIHRoaXMuaXRyID0gaXRyO1xuICAgIHRoaXMuZG9uZUNhbGxiYWNrID0gZG9uZUNhbGxiYWNrO1xuICB9XG4gIGFib3J0KCkge1xuICAgIHRoaXMuYWJvcnRDb250cm9sbGVyLmFib3J0KCk7XG4gIH1cbiAgYXN5bmMgKltTeW1ib2wuYXN5bmNJdGVyYXRvcl0oKSB7XG4gICAgZm9yIGF3YWl0IChjb25zdCBtZXNzYWdlIG9mIHRoaXMuaXRyKSB7XG4gICAgICBpZiAoXCJlcnJvclwiIGluIG1lc3NhZ2UpIHtcbiAgICAgICAgdGhyb3cgbmV3IEVycm9yKG1lc3NhZ2UuZXJyb3IpO1xuICAgICAgfVxuICAgICAgeWllbGQgbWVzc2FnZTtcbiAgICAgIGlmIChtZXNzYWdlLmRvbmUgfHwgbWVzc2FnZS5zdGF0dXMgPT09IFwic3VjY2Vzc1wiKSB7XG4gICAgICAgIHRoaXMuZG9uZUNhbGxiYWNrKCk7XG4gICAgICAgIHJldHVybjtcbiAgICAgIH1cbiAgICB9XG4gICAgdGhyb3cgbmV3IEVycm9yKFwiRGlkIG5vdCByZWNlaXZlIGRvbmUgb3Igc3VjY2VzcyByZXNwb25zZSBpbiBzdHJlYW0uXCIpO1xuICB9XG59XG5jb25zdCBjaGVja09rID0gYXN5bmMgKHJlc3BvbnNlKSA9PiB7XG4gIGlmIChyZXNwb25zZS5vaykge1xuICAgIHJldHVybjtcbiAgfVxuICBsZXQgbWVzc2FnZSA9IGBFcnJvciAke3Jlc3BvbnNlLnN0YXR1c306ICR7cmVzcG9uc2Uuc3RhdHVzVGV4dH1gO1xuICBsZXQgZXJyb3JEYXRhID0gbnVsbDtcbiAgaWYgKHJlc3BvbnNlLmhlYWRlcnMuZ2V0KFwiY29udGVudC10eXBlXCIpPy5pbmNsdWRlcyhcImFwcGxpY2F0aW9uL2pzb25cIikpIHtcbiAgICB0cnkge1xuICAgICAgZXJyb3JEYXRhID0gYXdhaXQgcmVzcG9uc2UuanNvbigpO1xuICAgICAgbWVzc2FnZSA9IGVycm9yRGF0YS5lcnJvciB8fCBtZXNzYWdlO1xuICAgIH0gY2F0Y2ggKGVycm9yKSB7XG4gICAgICBjb25zb2xlLmxvZyhcIkZhaWxlZCB0byBwYXJzZSBlcnJvciByZXNwb25zZSBhcyBKU09OXCIpO1xuICAgIH1cbiAgfSBlbHNlIHtcbiAgICB0cnkge1xuICAgICAgY29uc29sZS5sb2coXCJHZXR0aW5nIHRleHQgZnJvbSByZXNwb25zZVwiKTtcbiAgICAgIGNvbnN0IHRleHRSZXNwb25zZSA9IGF3YWl0IHJlc3BvbnNlLnRleHQoKTtcbiAgICAgIG1lc3NhZ2UgPSB0ZXh0UmVzcG9uc2UgfHwgbWVzc2FnZTtcbiAgICB9IGNhdGNoIChlcnJvcikge1xuICAgICAgY29uc29sZS5sb2coXCJGYWlsZWQgdG8gZ2V0IHRleHQgZnJvbSBlcnJvciByZXNwb25zZVwiKTtcbiAgICB9XG4gIH1cbiAgdGhyb3cgbmV3IFJlc3BvbnNlRXJyb3IobWVzc2FnZSwgcmVzcG9uc2Uuc3RhdHVzKTtcbn07XG5mdW5jdGlvbiBnZXRQbGF0Zm9ybSgpIHtcbiAgaWYgKHR5cGVvZiB3aW5kb3cgIT09IFwidW5kZWZpbmVkXCIgJiYgd2luZG93Lm5hdmlnYXRvcikge1xuICAgIGNvbnN0IG5hdiA9IG5hdmlnYXRvcjtcbiAgICBpZiAoXCJ1c2VyQWdlbnREYXRhXCIgaW4gbmF2ICYmIG5hdi51c2VyQWdlbnREYXRhPy5wbGF0Zm9ybSkge1xuICAgICAgcmV0dXJuIGAke25hdi51c2VyQWdlbnREYXRhLnBsYXRmb3JtLnRvTG93ZXJDYXNlKCl9IEJyb3dzZXIvJHtuYXZpZ2F0b3IudXNlckFnZW50fTtgO1xuICAgIH1cbiAgICBpZiAobmF2aWdhdG9yLnBsYXRmb3JtKSB7XG4gICAgICByZXR1cm4gYCR7bmF2aWdhdG9yLnBsYXRmb3JtLnRvTG93ZXJDYXNlKCl9IEJyb3dzZXIvJHtuYXZpZ2F0b3IudXNlckFnZW50fTtgO1xuICAgIH1cbiAgICByZXR1cm4gYHVua25vd24gQnJvd3Nlci8ke25hdmlnYXRvci51c2VyQWdlbnR9O2A7XG4gIH0gZWxzZSBpZiAodHlwZW9mIHByb2Nlc3MgIT09IFwidW5kZWZpbmVkXCIpIHtcbiAgICByZXR1cm4gYCR7cHJvY2Vzcy5hcmNofSAke3Byb2Nlc3MucGxhdGZvcm19IE5vZGUuanMvJHtwcm9jZXNzLnZlcnNpb259YDtcbiAgfVxuICByZXR1cm4gXCJcIjtcbn1cbmZ1bmN0aW9uIG5vcm1hbGl6ZUhlYWRlcnMoaGVhZGVycykge1xuICBpZiAoaGVhZGVycyBpbnN0YW5jZW9mIEhlYWRlcnMpIHtcbiAgICBjb25zdCBvYmogPSB7fTtcbiAgICBoZWFkZXJzLmZvckVhY2goKHZhbHVlLCBrZXkpID0+IHtcbiAgICAgIG9ialtrZXldID0gdmFsdWU7XG4gICAgfSk7XG4gICAgcmV0dXJuIG9iajtcbiAgfSBlbHNlIGlmIChBcnJheS5pc0FycmF5KGhlYWRlcnMpKSB7XG4gICAgcmV0dXJuIE9iamVjdC5mcm9tRW50cmllcyhoZWFkZXJzKTtcbiAgfSBlbHNlIHtcbiAgICByZXR1cm4gaGVhZGVycyB8fCB7fTtcbiAgfVxufVxuY29uc3QgcmVhZEVudlZhciA9IChvYmosIGtleSkgPT4ge1xuICByZXR1cm4gb2JqW2tleV07XG59O1xuY29uc3QgZmV0Y2hXaXRoSGVhZGVycyA9IGFzeW5jIChmZXRjaCwgdXJsLCBvcHRpb25zID0ge30pID0+IHtcbiAgY29uc3QgZGVmYXVsdEhlYWRlcnMgPSB7XG4gICAgXCJDb250ZW50LVR5cGVcIjogXCJhcHBsaWNhdGlvbi9qc29uXCIsXG4gICAgQWNjZXB0OiBcImFwcGxpY2F0aW9uL2pzb25cIixcbiAgICBcIlVzZXItQWdlbnRcIjogYG9sbGFtYS1qcy8ke3ZlcnNpb259ICgke2dldFBsYXRmb3JtKCl9KWBcbiAgfTtcbiAgb3B0aW9ucy5oZWFkZXJzID0gbm9ybWFsaXplSGVhZGVycyhvcHRpb25zLmhlYWRlcnMpO1xuICB0cnkge1xuICAgIGNvbnN0IHBhcnNlZCA9IG5ldyBVUkwodXJsKTtcbiAgICBpZiAocGFyc2VkLnByb3RvY29sID09PSBcImh0dHBzOlwiICYmIHBhcnNlZC5ob3N0bmFtZSA9PT0gXCJvbGxhbWEuY29tXCIpIHtcbiAgICAgIGNvbnN0IGFwaUtleSA9IHR5cGVvZiBwcm9jZXNzID09PSBcIm9iamVjdFwiICYmIHByb2Nlc3MgIT09IG51bGwgJiYgdHlwZW9mIHByb2Nlc3MuZW52ID09PSBcIm9iamVjdFwiICYmIHByb2Nlc3MuZW52ICE9PSBudWxsID8gcmVhZEVudlZhcihwcm9jZXNzLmVudiwgXCJPTExBTUFfQVBJX0tFWVwiKSA6IHZvaWQgMDtcbiAgICAgIGNvbnN0IGF1dGhvcml6YXRpb24gPSBvcHRpb25zLmhlYWRlcnNbXCJhdXRob3JpemF0aW9uXCJdIHx8IG9wdGlvbnMuaGVhZGVyc1tcIkF1dGhvcml6YXRpb25cIl07XG4gICAgICBpZiAoIWF1dGhvcml6YXRpb24gJiYgYXBpS2V5KSB7XG4gICAgICAgIG9wdGlvbnMuaGVhZGVyc1tcIkF1dGhvcml6YXRpb25cIl0gPSBgQmVhcmVyICR7YXBpS2V5fWA7XG4gICAgICB9XG4gICAgfVxuICB9IGNhdGNoIChlcnJvcikge1xuICAgIGNvbnNvbGUuZXJyb3IoXCJlcnJvciBwYXJzaW5nIHVybFwiLCBlcnJvcik7XG4gIH1cbiAgY29uc3QgY3VzdG9tSGVhZGVycyA9IE9iamVjdC5mcm9tRW50cmllcyhcbiAgICBPYmplY3QuZW50cmllcyhvcHRpb25zLmhlYWRlcnMpLmZpbHRlcihcbiAgICAgIChba2V5XSkgPT4gIU9iamVjdC5rZXlzKGRlZmF1bHRIZWFkZXJzKS5zb21lKFxuICAgICAgICAoZGVmYXVsdEtleSkgPT4gZGVmYXVsdEtleS50b0xvd2VyQ2FzZSgpID09PSBrZXkudG9Mb3dlckNhc2UoKVxuICAgICAgKVxuICAgIClcbiAgKTtcbiAgb3B0aW9ucy5oZWFkZXJzID0ge1xuICAgIC4uLmRlZmF1bHRIZWFkZXJzLFxuICAgIC4uLmN1c3RvbUhlYWRlcnNcbiAgfTtcbiAgcmV0dXJuIGZldGNoKHVybCwgb3B0aW9ucyk7XG59O1xuY29uc3QgZ2V0ID0gYXN5bmMgKGZldGNoLCBob3N0LCBvcHRpb25zKSA9PiB7XG4gIGNvbnN0IHJlc3BvbnNlID0gYXdhaXQgZmV0Y2hXaXRoSGVhZGVycyhmZXRjaCwgaG9zdCwge1xuICAgIGhlYWRlcnM6IG9wdGlvbnM/LmhlYWRlcnNcbiAgfSk7XG4gIGF3YWl0IGNoZWNrT2socmVzcG9uc2UpO1xuICByZXR1cm4gcmVzcG9uc2U7XG59O1xuY29uc3QgcG9zdCA9IGFzeW5jIChmZXRjaCwgaG9zdCwgZGF0YSwgb3B0aW9ucykgPT4ge1xuICBjb25zdCBpc1JlY29yZCA9IChpbnB1dCkgPT4ge1xuICAgIHJldHVybiBpbnB1dCAhPT0gbnVsbCAmJiB0eXBlb2YgaW5wdXQgPT09IFwib2JqZWN0XCIgJiYgIUFycmF5LmlzQXJyYXkoaW5wdXQpO1xuICB9O1xuICBjb25zdCBmb3JtYXR0ZWREYXRhID0gaXNSZWNvcmQoZGF0YSkgPyBKU09OLnN0cmluZ2lmeShkYXRhKSA6IGRhdGE7XG4gIGNvbnN0IHJlc3BvbnNlID0gYXdhaXQgZmV0Y2hXaXRoSGVhZGVycyhmZXRjaCwgaG9zdCwge1xuICAgIG1ldGhvZDogXCJQT1NUXCIsXG4gICAgYm9keTogZm9ybWF0dGVkRGF0YSxcbiAgICBzaWduYWw6IG9wdGlvbnM/LnNpZ25hbCxcbiAgICBoZWFkZXJzOiBvcHRpb25zPy5oZWFkZXJzXG4gIH0pO1xuICBhd2FpdCBjaGVja09rKHJlc3BvbnNlKTtcbiAgcmV0dXJuIHJlc3BvbnNlO1xufTtcbmNvbnN0IGRlbCA9IGFzeW5jIChmZXRjaCwgaG9zdCwgZGF0YSwgb3B0aW9ucykgPT4ge1xuICBjb25zdCByZXNwb25zZSA9IGF3YWl0IGZldGNoV2l0aEhlYWRlcnMoZmV0Y2gsIGhvc3QsIHtcbiAgICBtZXRob2Q6IFwiREVMRVRFXCIsXG4gICAgYm9keTogSlNPTi5zdHJpbmdpZnkoZGF0YSksXG4gICAgaGVhZGVyczogb3B0aW9ucz8uaGVhZGVyc1xuICB9KTtcbiAgYXdhaXQgY2hlY2tPayhyZXNwb25zZSk7XG4gIHJldHVybiByZXNwb25zZTtcbn07XG5jb25zdCBwYXJzZUpTT04gPSBhc3luYyBmdW5jdGlvbiogKGl0cikge1xuICBjb25zdCBkZWNvZGVyID0gbmV3IFRleHREZWNvZGVyKFwidXRmLThcIik7XG4gIGxldCBidWZmZXIgPSBcIlwiO1xuICBjb25zdCByZWFkZXIgPSBpdHIuZ2V0UmVhZGVyKCk7XG4gIHdoaWxlICh0cnVlKSB7XG4gICAgY29uc3QgeyBkb25lLCB2YWx1ZTogY2h1bmsgfSA9IGF3YWl0IHJlYWRlci5yZWFkKCk7XG4gICAgaWYgKGRvbmUpIHtcbiAgICAgIGJyZWFrO1xuICAgIH1cbiAgICBidWZmZXIgKz0gZGVjb2Rlci5kZWNvZGUoY2h1bmssIHsgc3RyZWFtOiB0cnVlIH0pO1xuICAgIGNvbnN0IHBhcnRzID0gYnVmZmVyLnNwbGl0KFwiXFxuXCIpO1xuICAgIGJ1ZmZlciA9IHBhcnRzLnBvcCgpID8/IFwiXCI7XG4gICAgZm9yIChjb25zdCBwYXJ0IG9mIHBhcnRzKSB7XG4gICAgICB0cnkge1xuICAgICAgICB5aWVsZCBKU09OLnBhcnNlKHBhcnQpO1xuICAgICAgfSBjYXRjaCAoZXJyb3IpIHtcbiAgICAgICAgY29uc29sZS53YXJuKFwiaW52YWxpZCBqc29uOiBcIiwgcGFydCk7XG4gICAgICB9XG4gICAgfVxuICB9XG4gIGJ1ZmZlciArPSBkZWNvZGVyLmRlY29kZSgpO1xuICBmb3IgKGNvbnN0IHBhcnQgb2YgYnVmZmVyLnNwbGl0KFwiXFxuXCIpLmZpbHRlcigocCkgPT4gcCAhPT0gXCJcIikpIHtcbiAgICB0cnkge1xuICAgICAgeWllbGQgSlNPTi5wYXJzZShwYXJ0KTtcbiAgICB9IGNhdGNoIChlcnJvcikge1xuICAgICAgY29uc29sZS53YXJuKFwiaW52YWxpZCBqc29uOiBcIiwgcGFydCk7XG4gICAgfVxuICB9XG59O1xuY29uc3QgZm9ybWF0SG9zdCA9IChob3N0KSA9PiB7XG4gIGlmICghaG9zdCkge1xuICAgIHJldHVybiBkZWZhdWx0SG9zdDtcbiAgfVxuICBsZXQgaXNFeHBsaWNpdFByb3RvY29sID0gaG9zdC5pbmNsdWRlcyhcIjovL1wiKTtcbiAgaWYgKGhvc3Quc3RhcnRzV2l0aChcIjpcIikpIHtcbiAgICBob3N0ID0gYGh0dHA6Ly8xMjcuMC4wLjEke2hvc3R9YDtcbiAgICBpc0V4cGxpY2l0UHJvdG9jb2wgPSB0cnVlO1xuICB9XG4gIGlmICghaXNFeHBsaWNpdFByb3RvY29sKSB7XG4gICAgaG9zdCA9IGBodHRwOi8vJHtob3N0fWA7XG4gIH1cbiAgY29uc3QgdXJsID0gbmV3IFVSTChob3N0KTtcbiAgbGV0IHBvcnQgPSB1cmwucG9ydDtcbiAgaWYgKCFwb3J0KSB7XG4gICAgaWYgKCFpc0V4cGxpY2l0UHJvdG9jb2wpIHtcbiAgICAgIHBvcnQgPSBkZWZhdWx0UG9ydDtcbiAgICB9IGVsc2Uge1xuICAgICAgcG9ydCA9IHVybC5wcm90b2NvbCA9PT0gXCJodHRwczpcIiA/IFwiNDQzXCIgOiBcIjgwXCI7XG4gICAgfVxuICB9XG4gIGxldCBhdXRoID0gXCJcIjtcbiAgaWYgKHVybC51c2VybmFtZSkge1xuICAgIGF1dGggPSB1cmwudXNlcm5hbWU7XG4gICAgaWYgKHVybC5wYXNzd29yZCkge1xuICAgICAgYXV0aCArPSBgOiR7dXJsLnBhc3N3b3JkfWA7XG4gICAgfVxuICAgIGF1dGggKz0gXCJAXCI7XG4gIH1cbiAgbGV0IGZvcm1hdHRlZEhvc3QgPSBgJHt1cmwucHJvdG9jb2x9Ly8ke2F1dGh9JHt1cmwuaG9zdG5hbWV9OiR7cG9ydH0ke3VybC5wYXRobmFtZX1gO1xuICBpZiAoZm9ybWF0dGVkSG9zdC5lbmRzV2l0aChcIi9cIikpIHtcbiAgICBmb3JtYXR0ZWRIb3N0ID0gZm9ybWF0dGVkSG9zdC5zbGljZSgwLCAtMSk7XG4gIH1cbiAgcmV0dXJuIGZvcm1hdHRlZEhvc3Q7XG59O1xuXG52YXIgX19kZWZQcm9wID0gT2JqZWN0LmRlZmluZVByb3BlcnR5O1xudmFyIF9fZGVmTm9ybWFsUHJvcCA9IChvYmosIGtleSwgdmFsdWUpID0+IGtleSBpbiBvYmogPyBfX2RlZlByb3Aob2JqLCBrZXksIHsgZW51bWVyYWJsZTogdHJ1ZSwgY29uZmlndXJhYmxlOiB0cnVlLCB3cml0YWJsZTogdHJ1ZSwgdmFsdWUgfSkgOiBvYmpba2V5XSA9IHZhbHVlO1xudmFyIF9fcHVibGljRmllbGQgPSAob2JqLCBrZXksIHZhbHVlKSA9PiB7XG4gIF9fZGVmTm9ybWFsUHJvcChvYmosIHR5cGVvZiBrZXkgIT09IFwic3ltYm9sXCIgPyBrZXkgKyBcIlwiIDoga2V5LCB2YWx1ZSk7XG4gIHJldHVybiB2YWx1ZTtcbn07XG5sZXQgT2xsYW1hJDEgPSBjbGFzcyBPbGxhbWEge1xuICBjb25zdHJ1Y3Rvcihjb25maWcpIHtcbiAgICBfX3B1YmxpY0ZpZWxkKHRoaXMsIFwiY29uZmlnXCIpO1xuICAgIF9fcHVibGljRmllbGQodGhpcywgXCJmZXRjaFwiKTtcbiAgICBfX3B1YmxpY0ZpZWxkKHRoaXMsIFwib25nb2luZ1N0cmVhbWVkUmVxdWVzdHNcIiwgW10pO1xuICAgIHRoaXMuY29uZmlnID0ge1xuICAgICAgaG9zdDogXCJcIixcbiAgICAgIGhlYWRlcnM6IGNvbmZpZz8uaGVhZGVyc1xuICAgIH07XG4gICAgaWYgKCFjb25maWc/LnByb3h5KSB7XG4gICAgICB0aGlzLmNvbmZpZy5ob3N0ID0gZm9ybWF0SG9zdChjb25maWc/Lmhvc3QgPz8gZGVmYXVsdEhvc3QpO1xuICAgIH1cbiAgICB0aGlzLmZldGNoID0gY29uZmlnPy5mZXRjaCA/PyBmZXRjaDtcbiAgfVxuICAvLyBBYm9ydCBhbnkgb25nb2luZyBzdHJlYW1lZCByZXF1ZXN0cyB0byBPbGxhbWFcbiAgYWJvcnQoKSB7XG4gICAgZm9yIChjb25zdCByZXF1ZXN0IG9mIHRoaXMub25nb2luZ1N0cmVhbWVkUmVxdWVzdHMpIHtcbiAgICAgIHJlcXVlc3QuYWJvcnQoKTtcbiAgICB9XG4gICAgdGhpcy5vbmdvaW5nU3RyZWFtZWRSZXF1ZXN0cy5sZW5ndGggPSAwO1xuICB9XG4gIC8qKlxuICAgKiBQcm9jZXNzZXMgYSByZXF1ZXN0IHRvIHRoZSBPbGxhbWEgc2VydmVyLiBJZiB0aGUgcmVxdWVzdCBpcyBzdHJlYW1hYmxlLCBpdCB3aWxsIHJldHVybiBhXG4gICAqIEFib3J0YWJsZUFzeW5jSXRlcmF0b3IgdGhhdCB5aWVsZHMgdGhlIHJlc3BvbnNlIG1lc3NhZ2VzLiBPdGhlcndpc2UsIGl0IHdpbGwgcmV0dXJuIHRoZSByZXNwb25zZVxuICAgKiBvYmplY3QuXG4gICAqIEBwYXJhbSBlbmRwb2ludCB7c3RyaW5nfSAtIFRoZSBlbmRwb2ludCB0byBzZW5kIHRoZSByZXF1ZXN0IHRvLlxuICAgKiBAcGFyYW0gcmVxdWVzdCB7b2JqZWN0fSAtIFRoZSByZXF1ZXN0IG9iamVjdCB0byBzZW5kIHRvIHRoZSBlbmRwb2ludC5cbiAgICogQHByb3RlY3RlZCB7VCB8IEFib3J0YWJsZUFzeW5jSXRlcmF0b3I8VD59IC0gVGhlIHJlc3BvbnNlIG9iamVjdCBvciBhIEFib3J0YWJsZUFzeW5jSXRlcmF0b3IgdGhhdCB5aWVsZHNcbiAgICogcmVzcG9uc2UgbWVzc2FnZXMuXG4gICAqIEB0aHJvd3Mge0Vycm9yfSAtIElmIHRoZSByZXNwb25zZSBib2R5IGlzIG1pc3Npbmcgb3IgaWYgdGhlIHJlc3BvbnNlIGlzIGFuIGVycm9yLlxuICAgKiBAcmV0dXJucyB7UHJvbWlzZTxUIHwgQWJvcnRhYmxlQXN5bmNJdGVyYXRvcjxUPj59IC0gVGhlIHJlc3BvbnNlIG9iamVjdCBvciBhIEFib3J0YWJsZUFzeW5jSXRlcmF0b3IgdGhhdCB5aWVsZHMgdGhlIHN0cmVhbWVkIHJlc3BvbnNlLlxuICAgKi9cbiAgYXN5bmMgcHJvY2Vzc1N0cmVhbWFibGVSZXF1ZXN0KGVuZHBvaW50LCByZXF1ZXN0KSB7XG4gICAgcmVxdWVzdC5zdHJlYW0gPSByZXF1ZXN0LnN0cmVhbSA/PyBmYWxzZTtcbiAgICBjb25zdCBob3N0ID0gYCR7dGhpcy5jb25maWcuaG9zdH0vYXBpLyR7ZW5kcG9pbnR9YDtcbiAgICBpZiAocmVxdWVzdC5zdHJlYW0pIHtcbiAgICAgIGNvbnN0IGFib3J0Q29udHJvbGxlciA9IG5ldyBBYm9ydENvbnRyb2xsZXIoKTtcbiAgICAgIGNvbnN0IHJlc3BvbnNlMiA9IGF3YWl0IHBvc3QodGhpcy5mZXRjaCwgaG9zdCwgcmVxdWVzdCwge1xuICAgICAgICBzaWduYWw6IGFib3J0Q29udHJvbGxlci5zaWduYWwsXG4gICAgICAgIGhlYWRlcnM6IHRoaXMuY29uZmlnLmhlYWRlcnNcbiAgICAgIH0pO1xuICAgICAgaWYgKCFyZXNwb25zZTIuYm9keSkge1xuICAgICAgICB0aHJvdyBuZXcgRXJyb3IoXCJNaXNzaW5nIGJvZHlcIik7XG4gICAgICB9XG4gICAgICBjb25zdCBpdHIgPSBwYXJzZUpTT04ocmVzcG9uc2UyLmJvZHkpO1xuICAgICAgY29uc3QgYWJvcnRhYmxlQXN5bmNJdGVyYXRvciA9IG5ldyBBYm9ydGFibGVBc3luY0l0ZXJhdG9yKFxuICAgICAgICBhYm9ydENvbnRyb2xsZXIsXG4gICAgICAgIGl0cixcbiAgICAgICAgKCkgPT4ge1xuICAgICAgICAgIGNvbnN0IGkgPSB0aGlzLm9uZ29pbmdTdHJlYW1lZFJlcXVlc3RzLmluZGV4T2YoYWJvcnRhYmxlQXN5bmNJdGVyYXRvcik7XG4gICAgICAgICAgaWYgKGkgPiAtMSkge1xuICAgICAgICAgICAgdGhpcy5vbmdvaW5nU3RyZWFtZWRSZXF1ZXN0cy5zcGxpY2UoaSwgMSk7XG4gICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICApO1xuICAgICAgdGhpcy5vbmdvaW5nU3RyZWFtZWRSZXF1ZXN0cy5wdXNoKGFib3J0YWJsZUFzeW5jSXRlcmF0b3IpO1xuICAgICAgcmV0dXJuIGFib3J0YWJsZUFzeW5jSXRlcmF0b3I7XG4gICAgfVxuICAgIGNvbnN0IHJlc3BvbnNlID0gYXdhaXQgcG9zdCh0aGlzLmZldGNoLCBob3N0LCByZXF1ZXN0LCB7XG4gICAgICBoZWFkZXJzOiB0aGlzLmNvbmZpZy5oZWFkZXJzXG4gICAgfSk7XG4gICAgcmV0dXJuIGF3YWl0IHJlc3BvbnNlLmpzb24oKTtcbiAgfVxuICAvKipcbiAgICogRW5jb2RlcyBhbiBpbWFnZSB0byBiYXNlNjQgaWYgaXQgaXMgYSBVaW50OEFycmF5LlxuICAgKiBAcGFyYW0gaW1hZ2Uge1VpbnQ4QXJyYXkgfCBzdHJpbmd9IC0gVGhlIGltYWdlIHRvIGVuY29kZS5cbiAgICogQHJldHVybnMge1Byb21pc2U8c3RyaW5nPn0gLSBUaGUgYmFzZTY0IGVuY29kZWQgaW1hZ2UuXG4gICAqL1xuICBhc3luYyBlbmNvZGVJbWFnZShpbWFnZSkge1xuICAgIGlmICh0eXBlb2YgaW1hZ2UgIT09IFwic3RyaW5nXCIpIHtcbiAgICAgIGNvbnN0IHVpbnQ4QXJyYXkgPSBuZXcgVWludDhBcnJheShpbWFnZSk7XG4gICAgICBsZXQgYnl0ZVN0cmluZyA9IFwiXCI7XG4gICAgICBjb25zdCBsZW4gPSB1aW50OEFycmF5LmJ5dGVMZW5ndGg7XG4gICAgICBmb3IgKGxldCBpID0gMDsgaSA8IGxlbjsgaSsrKSB7XG4gICAgICAgIGJ5dGVTdHJpbmcgKz0gU3RyaW5nLmZyb21DaGFyQ29kZSh1aW50OEFycmF5W2ldKTtcbiAgICAgIH1cbiAgICAgIHJldHVybiBidG9hKGJ5dGVTdHJpbmcpO1xuICAgIH1cbiAgICByZXR1cm4gaW1hZ2U7XG4gIH1cbiAgLyoqXG4gICAqIEdlbmVyYXRlcyBhIHJlc3BvbnNlIGZyb20gYSB0ZXh0IHByb21wdC5cbiAgICogQHBhcmFtIHJlcXVlc3Qge0dlbmVyYXRlUmVxdWVzdH0gLSBUaGUgcmVxdWVzdCBvYmplY3QuXG4gICAqIEByZXR1cm5zIHtQcm9taXNlPEdlbmVyYXRlUmVzcG9uc2UgfCBBYm9ydGFibGVBc3luY0l0ZXJhdG9yPEdlbmVyYXRlUmVzcG9uc2U+Pn0gLSBUaGUgcmVzcG9uc2Ugb2JqZWN0IG9yXG4gICAqIGFuIEFib3J0YWJsZUFzeW5jSXRlcmF0b3IgdGhhdCB5aWVsZHMgcmVzcG9uc2UgbWVzc2FnZXMuXG4gICAqL1xuICBhc3luYyBnZW5lcmF0ZShyZXF1ZXN0KSB7XG4gICAgaWYgKHJlcXVlc3QuaW1hZ2VzKSB7XG4gICAgICByZXF1ZXN0LmltYWdlcyA9IGF3YWl0IFByb21pc2UuYWxsKHJlcXVlc3QuaW1hZ2VzLm1hcCh0aGlzLmVuY29kZUltYWdlLmJpbmQodGhpcykpKTtcbiAgICB9XG4gICAgcmV0dXJuIHRoaXMucHJvY2Vzc1N0cmVhbWFibGVSZXF1ZXN0KFwiZ2VuZXJhdGVcIiwgcmVxdWVzdCk7XG4gIH1cbiAgLyoqXG4gICAqIENoYXRzIHdpdGggdGhlIG1vZGVsLiBUaGUgcmVxdWVzdCBvYmplY3QgY2FuIGNvbnRhaW4gbWVzc2FnZXMgd2l0aCBpbWFnZXMgdGhhdCBhcmUgZWl0aGVyXG4gICAqIFVpbnQ4QXJyYXlzIG9yIGJhc2U2NCBlbmNvZGVkIHN0cmluZ3MuIFRoZSBpbWFnZXMgd2lsbCBiZSBiYXNlNjQgZW5jb2RlZCBiZWZvcmUgc2VuZGluZyB0aGVcbiAgICogcmVxdWVzdC5cbiAgICogQHBhcmFtIHJlcXVlc3Qge0NoYXRSZXF1ZXN0fSAtIFRoZSByZXF1ZXN0IG9iamVjdC5cbiAgICogQHJldHVybnMge1Byb21pc2U8Q2hhdFJlc3BvbnNlIHwgQWJvcnRhYmxlQXN5bmNJdGVyYXRvcjxDaGF0UmVzcG9uc2U+Pn0gLSBUaGUgcmVzcG9uc2Ugb2JqZWN0IG9yIGFuXG4gICAqIEFib3J0YWJsZUFzeW5jSXRlcmF0b3IgdGhhdCB5aWVsZHMgcmVzcG9uc2UgbWVzc2FnZXMuXG4gICAqL1xuICBhc3luYyBjaGF0KHJlcXVlc3QpIHtcbiAgICBpZiAocmVxdWVzdC5tZXNzYWdlcykge1xuICAgICAgZm9yIChjb25zdCBtZXNzYWdlIG9mIHJlcXVlc3QubWVzc2FnZXMpIHtcbiAgICAgICAgaWYgKG1lc3NhZ2UuaW1hZ2VzKSB7XG4gICAgICAgICAgbWVzc2FnZS5pbWFnZXMgPSBhd2FpdCBQcm9taXNlLmFsbChcbiAgICAgICAgICAgIG1lc3NhZ2UuaW1hZ2VzLm1hcCh0aGlzLmVuY29kZUltYWdlLmJpbmQodGhpcykpXG4gICAgICAgICAgKTtcbiAgICAgICAgfVxuICAgICAgfVxuICAgIH1cbiAgICByZXR1cm4gdGhpcy5wcm9jZXNzU3RyZWFtYWJsZVJlcXVlc3QoXCJjaGF0XCIsIHJlcXVlc3QpO1xuICB9XG4gIC8qKlxuICAgKiBDcmVhdGVzIGEgbmV3IG1vZGVsIGZyb20gYSBzdHJlYW0gb2YgZGF0YS5cbiAgICogQHBhcmFtIHJlcXVlc3Qge0NyZWF0ZVJlcXVlc3R9IC0gVGhlIHJlcXVlc3Qgb2JqZWN0LlxuICAgKiBAcmV0dXJucyB7UHJvbWlzZTxQcm9ncmVzc1Jlc3BvbnNlIHwgQWJvcnRhYmxlQXN5bmNJdGVyYXRvcjxQcm9ncmVzc1Jlc3BvbnNlPj59IC0gVGhlIHJlc3BvbnNlIG9iamVjdCBvciBhIHN0cmVhbSBvZiBwcm9ncmVzcyByZXNwb25zZXMuXG4gICAqL1xuICBhc3luYyBjcmVhdGUocmVxdWVzdCkge1xuICAgIHJldHVybiB0aGlzLnByb2Nlc3NTdHJlYW1hYmxlUmVxdWVzdChcImNyZWF0ZVwiLCB7XG4gICAgICAuLi5yZXF1ZXN0XG4gICAgfSk7XG4gIH1cbiAgLyoqXG4gICAqIFB1bGxzIGEgbW9kZWwgZnJvbSB0aGUgT2xsYW1hIHJlZ2lzdHJ5LiBUaGUgcmVxdWVzdCBvYmplY3QgY2FuIGNvbnRhaW4gYSBzdHJlYW0gZmxhZyB0byBpbmRpY2F0ZSBpZiB0aGVcbiAgICogcmVzcG9uc2Ugc2hvdWxkIGJlIHN0cmVhbWVkLlxuICAgKiBAcGFyYW0gcmVxdWVzdCB7UHVsbFJlcXVlc3R9IC0gVGhlIHJlcXVlc3Qgb2JqZWN0LlxuICAgKiBAcmV0dXJucyB7UHJvbWlzZTxQcm9ncmVzc1Jlc3BvbnNlIHwgQWJvcnRhYmxlQXN5bmNJdGVyYXRvcjxQcm9ncmVzc1Jlc3BvbnNlPj59IC0gVGhlIHJlc3BvbnNlIG9iamVjdCBvclxuICAgKiBhbiBBYm9ydGFibGVBc3luY0l0ZXJhdG9yIHRoYXQgeWllbGRzIHJlc3BvbnNlIG1lc3NhZ2VzLlxuICAgKi9cbiAgYXN5bmMgcHVsbChyZXF1ZXN0KSB7XG4gICAgcmV0dXJuIHRoaXMucHJvY2Vzc1N0cmVhbWFibGVSZXF1ZXN0KFwicHVsbFwiLCB7XG4gICAgICBuYW1lOiByZXF1ZXN0Lm1vZGVsLFxuICAgICAgc3RyZWFtOiByZXF1ZXN0LnN0cmVhbSxcbiAgICAgIGluc2VjdXJlOiByZXF1ZXN0Lmluc2VjdXJlXG4gICAgfSk7XG4gIH1cbiAgLyoqXG4gICAqIFB1c2hlcyBhIG1vZGVsIHRvIHRoZSBPbGxhbWEgcmVnaXN0cnkuIFRoZSByZXF1ZXN0IG9iamVjdCBjYW4gY29udGFpbiBhIHN0cmVhbSBmbGFnIHRvIGluZGljYXRlIGlmIHRoZVxuICAgKiByZXNwb25zZSBzaG91bGQgYmUgc3RyZWFtZWQuXG4gICAqIEBwYXJhbSByZXF1ZXN0IHtQdXNoUmVxdWVzdH0gLSBUaGUgcmVxdWVzdCBvYmplY3QuXG4gICAqIEByZXR1cm5zIHtQcm9taXNlPFByb2dyZXNzUmVzcG9uc2UgfCBBYm9ydGFibGVBc3luY0l0ZXJhdG9yPFByb2dyZXNzUmVzcG9uc2U+Pn0gLSBUaGUgcmVzcG9uc2Ugb2JqZWN0IG9yXG4gICAqIGFuIEFib3J0YWJsZUFzeW5jSXRlcmF0b3IgdGhhdCB5aWVsZHMgcmVzcG9uc2UgbWVzc2FnZXMuXG4gICAqL1xuICBhc3luYyBwdXNoKHJlcXVlc3QpIHtcbiAgICByZXR1cm4gdGhpcy5wcm9jZXNzU3RyZWFtYWJsZVJlcXVlc3QoXCJwdXNoXCIsIHtcbiAgICAgIG5hbWU6IHJlcXVlc3QubW9kZWwsXG4gICAgICBzdHJlYW06IHJlcXVlc3Quc3RyZWFtLFxuICAgICAgaW5zZWN1cmU6IHJlcXVlc3QuaW5zZWN1cmVcbiAgICB9KTtcbiAgfVxuICAvKipcbiAgICogRGVsZXRlcyBhIG1vZGVsIGZyb20gdGhlIHNlcnZlci4gVGhlIHJlcXVlc3Qgb2JqZWN0IHNob3VsZCBjb250YWluIHRoZSBuYW1lIG9mIHRoZSBtb2RlbCB0b1xuICAgKiBkZWxldGUuXG4gICAqIEBwYXJhbSByZXF1ZXN0IHtEZWxldGVSZXF1ZXN0fSAtIFRoZSByZXF1ZXN0IG9iamVjdC5cbiAgICogQHJldHVybnMge1Byb21pc2U8U3RhdHVzUmVzcG9uc2U+fSAtIFRoZSByZXNwb25zZSBvYmplY3QuXG4gICAqL1xuICBhc3luYyBkZWxldGUocmVxdWVzdCkge1xuICAgIGF3YWl0IGRlbChcbiAgICAgIHRoaXMuZmV0Y2gsXG4gICAgICBgJHt0aGlzLmNvbmZpZy5ob3N0fS9hcGkvZGVsZXRlYCxcbiAgICAgIHsgbmFtZTogcmVxdWVzdC5tb2RlbCB9LFxuICAgICAgeyBoZWFkZXJzOiB0aGlzLmNvbmZpZy5oZWFkZXJzIH1cbiAgICApO1xuICAgIHJldHVybiB7IHN0YXR1czogXCJzdWNjZXNzXCIgfTtcbiAgfVxuICAvKipcbiAgICogQ29waWVzIGEgbW9kZWwgZnJvbSBvbmUgbmFtZSB0byBhbm90aGVyLiBUaGUgcmVxdWVzdCBvYmplY3Qgc2hvdWxkIGNvbnRhaW4gdGhlIG5hbWUgb2YgdGhlXG4gICAqIG1vZGVsIHRvIGNvcHkgYW5kIHRoZSBuZXcgbmFtZS5cbiAgICogQHBhcmFtIHJlcXVlc3Qge0NvcHlSZXF1ZXN0fSAtIFRoZSByZXF1ZXN0IG9iamVjdC5cbiAgICogQHJldHVybnMge1Byb21pc2U8U3RhdHVzUmVzcG9uc2U+fSAtIFRoZSByZXNwb25zZSBvYmplY3QuXG4gICAqL1xuICBhc3luYyBjb3B5KHJlcXVlc3QpIHtcbiAgICBhd2FpdCBwb3N0KHRoaXMuZmV0Y2gsIGAke3RoaXMuY29uZmlnLmhvc3R9L2FwaS9jb3B5YCwgeyAuLi5yZXF1ZXN0IH0sIHtcbiAgICAgIGhlYWRlcnM6IHRoaXMuY29uZmlnLmhlYWRlcnNcbiAgICB9KTtcbiAgICByZXR1cm4geyBzdGF0dXM6IFwic3VjY2Vzc1wiIH07XG4gIH1cbiAgLyoqXG4gICAqIExpc3RzIHRoZSBtb2RlbHMgb24gdGhlIHNlcnZlci5cbiAgICogQHJldHVybnMge1Byb21pc2U8TGlzdFJlc3BvbnNlPn0gLSBUaGUgcmVzcG9uc2Ugb2JqZWN0LlxuICAgKiBAdGhyb3dzIHtFcnJvcn0gLSBJZiB0aGUgcmVzcG9uc2UgYm9keSBpcyBtaXNzaW5nLlxuICAgKi9cbiAgYXN5bmMgbGlzdCgpIHtcbiAgICBjb25zdCByZXNwb25zZSA9IGF3YWl0IGdldCh0aGlzLmZldGNoLCBgJHt0aGlzLmNvbmZpZy5ob3N0fS9hcGkvdGFnc2AsIHtcbiAgICAgIGhlYWRlcnM6IHRoaXMuY29uZmlnLmhlYWRlcnNcbiAgICB9KTtcbiAgICByZXR1cm4gYXdhaXQgcmVzcG9uc2UuanNvbigpO1xuICB9XG4gIC8qKlxuICAgKiBTaG93cyB0aGUgbWV0YWRhdGEgb2YgYSBtb2RlbC4gVGhlIHJlcXVlc3Qgb2JqZWN0IHNob3VsZCBjb250YWluIHRoZSBuYW1lIG9mIHRoZSBtb2RlbC5cbiAgICogQHBhcmFtIHJlcXVlc3Qge1Nob3dSZXF1ZXN0fSAtIFRoZSByZXF1ZXN0IG9iamVjdC5cbiAgICogQHJldHVybnMge1Byb21pc2U8U2hvd1Jlc3BvbnNlPn0gLSBUaGUgcmVzcG9uc2Ugb2JqZWN0LlxuICAgKi9cbiAgYXN5bmMgc2hvdyhyZXF1ZXN0KSB7XG4gICAgY29uc3QgcmVzcG9uc2UgPSBhd2FpdCBwb3N0KHRoaXMuZmV0Y2gsIGAke3RoaXMuY29uZmlnLmhvc3R9L2FwaS9zaG93YCwge1xuICAgICAgLi4ucmVxdWVzdFxuICAgIH0sIHtcbiAgICAgIGhlYWRlcnM6IHRoaXMuY29uZmlnLmhlYWRlcnNcbiAgICB9KTtcbiAgICByZXR1cm4gYXdhaXQgcmVzcG9uc2UuanNvbigpO1xuICB9XG4gIC8qKlxuICAgKiBFbWJlZHMgdGV4dCBpbnB1dCBpbnRvIHZlY3RvcnMuXG4gICAqIEBwYXJhbSByZXF1ZXN0IHtFbWJlZFJlcXVlc3R9IC0gVGhlIHJlcXVlc3Qgb2JqZWN0LlxuICAgKiBAcmV0dXJucyB7UHJvbWlzZTxFbWJlZFJlc3BvbnNlPn0gLSBUaGUgcmVzcG9uc2Ugb2JqZWN0LlxuICAgKi9cbiAgYXN5bmMgZW1iZWQocmVxdWVzdCkge1xuICAgIGNvbnN0IHJlc3BvbnNlID0gYXdhaXQgcG9zdCh0aGlzLmZldGNoLCBgJHt0aGlzLmNvbmZpZy5ob3N0fS9hcGkvZW1iZWRgLCB7XG4gICAgICAuLi5yZXF1ZXN0XG4gICAgfSwge1xuICAgICAgaGVhZGVyczogdGhpcy5jb25maWcuaGVhZGVyc1xuICAgIH0pO1xuICAgIHJldHVybiBhd2FpdCByZXNwb25zZS5qc29uKCk7XG4gIH1cbiAgLyoqXG4gICAqIEVtYmVkcyBhIHRleHQgcHJvbXB0IGludG8gYSB2ZWN0b3IuXG4gICAqIEBwYXJhbSByZXF1ZXN0IHtFbWJlZGRpbmdzUmVxdWVzdH0gLSBUaGUgcmVxdWVzdCBvYmplY3QuXG4gICAqIEByZXR1cm5zIHtQcm9taXNlPEVtYmVkZGluZ3NSZXNwb25zZT59IC0gVGhlIHJlc3BvbnNlIG9iamVjdC5cbiAgICovXG4gIGFzeW5jIGVtYmVkZGluZ3MocmVxdWVzdCkge1xuICAgIGNvbnN0IHJlc3BvbnNlID0gYXdhaXQgcG9zdCh0aGlzLmZldGNoLCBgJHt0aGlzLmNvbmZpZy5ob3N0fS9hcGkvZW1iZWRkaW5nc2AsIHtcbiAgICAgIC4uLnJlcXVlc3RcbiAgICB9LCB7XG4gICAgICBoZWFkZXJzOiB0aGlzLmNvbmZpZy5oZWFkZXJzXG4gICAgfSk7XG4gICAgcmV0dXJuIGF3YWl0IHJlc3BvbnNlLmpzb24oKTtcbiAgfVxuICAvKipcbiAgICogTGlzdHMgdGhlIHJ1bm5pbmcgbW9kZWxzIG9uIHRoZSBzZXJ2ZXJcbiAgICogQHJldHVybnMge1Byb21pc2U8TGlzdFJlc3BvbnNlPn0gLSBUaGUgcmVzcG9uc2Ugb2JqZWN0LlxuICAgKiBAdGhyb3dzIHtFcnJvcn0gLSBJZiB0aGUgcmVzcG9uc2UgYm9keSBpcyBtaXNzaW5nLlxuICAgKi9cbiAgYXN5bmMgcHMoKSB7XG4gICAgY29uc3QgcmVzcG9uc2UgPSBhd2FpdCBnZXQodGhpcy5mZXRjaCwgYCR7dGhpcy5jb25maWcuaG9zdH0vYXBpL3BzYCwge1xuICAgICAgaGVhZGVyczogdGhpcy5jb25maWcuaGVhZGVyc1xuICAgIH0pO1xuICAgIHJldHVybiBhd2FpdCByZXNwb25zZS5qc29uKCk7XG4gIH1cbiAgLyoqXG4gICAqIFJldHVybnMgdGhlIE9sbGFtYSBzZXJ2ZXIgdmVyc2lvbi5cbiAgICogQHJldHVybnMge1Byb21pc2U8VmVyc2lvblJlc3BvbnNlPn0gLSBUaGUgc2VydmVyIHZlcnNpb24gb2JqZWN0LlxuICAgKi9cbiAgYXN5bmMgdmVyc2lvbigpIHtcbiAgICBjb25zdCByZXNwb25zZSA9IGF3YWl0IGdldCh0aGlzLmZldGNoLCBgJHt0aGlzLmNvbmZpZy5ob3N0fS9hcGkvdmVyc2lvbmAsIHtcbiAgICAgIGhlYWRlcnM6IHRoaXMuY29uZmlnLmhlYWRlcnNcbiAgICB9KTtcbiAgICByZXR1cm4gYXdhaXQgcmVzcG9uc2UuanNvbigpO1xuICB9XG4gIC8qKlxuICAgKiBQZXJmb3JtcyB3ZWIgc2VhcmNoIHVzaW5nIHRoZSBPbGxhbWEgd2ViIHNlYXJjaCBBUElcbiAgICogQHBhcmFtIHJlcXVlc3Qge1dlYlNlYXJjaFJlcXVlc3R9IC0gVGhlIHNlYXJjaCByZXF1ZXN0IGNvbnRhaW5pbmcgcXVlcnkgYW5kIG9wdGlvbnNcbiAgICogQHJldHVybnMge1Byb21pc2U8V2ViU2VhcmNoUmVzcG9uc2U+fSAtIFRoZSBzZWFyY2ggcmVzdWx0c1xuICAgKiBAdGhyb3dzIHtFcnJvcn0gLSBJZiB0aGUgcmVxdWVzdCBpcyBpbnZhbGlkIG9yIHRoZSBzZXJ2ZXIgcmV0dXJucyBhbiBlcnJvclxuICAgKi9cbiAgYXN5bmMgd2ViU2VhcmNoKHJlcXVlc3QpIHtcbiAgICBpZiAoIXJlcXVlc3QucXVlcnkgfHwgcmVxdWVzdC5xdWVyeS5sZW5ndGggPT09IDApIHtcbiAgICAgIHRocm93IG5ldyBFcnJvcihcIlF1ZXJ5IGlzIHJlcXVpcmVkXCIpO1xuICAgIH1cbiAgICBjb25zdCByZXNwb25zZSA9IGF3YWl0IHBvc3QodGhpcy5mZXRjaCwgYGh0dHBzOi8vb2xsYW1hLmNvbS9hcGkvd2ViX3NlYXJjaGAsIHsgLi4ucmVxdWVzdCB9LCB7XG4gICAgICBoZWFkZXJzOiB0aGlzLmNvbmZpZy5oZWFkZXJzXG4gICAgfSk7XG4gICAgcmV0dXJuIGF3YWl0IHJlc3BvbnNlLmpzb24oKTtcbiAgfVxuICAvKipcbiAgICogRmV0Y2hlcyBhIHNpbmdsZSBwYWdlIHVzaW5nIHRoZSBPbGxhbWEgd2ViIGZldGNoIEFQSVxuICAgKiBAcGFyYW0gcmVxdWVzdCB7V2ViRmV0Y2hSZXF1ZXN0fSAtIFRoZSBmZXRjaCByZXF1ZXN0IGNvbnRhaW5pbmcgYSBVUkxcbiAgICogQHJldHVybnMge1Byb21pc2U8V2ViRmV0Y2hSZXNwb25zZT59IC0gVGhlIGZldGNoIHJlc3VsdFxuICAgKiBAdGhyb3dzIHtFcnJvcn0gLSBJZiB0aGUgcmVxdWVzdCBpcyBpbnZhbGlkIG9yIHRoZSBzZXJ2ZXIgcmV0dXJucyBhbiBlcnJvclxuICAgKi9cbiAgYXN5bmMgd2ViRmV0Y2gocmVxdWVzdCkge1xuICAgIGlmICghcmVxdWVzdC51cmwgfHwgcmVxdWVzdC51cmwubGVuZ3RoID09PSAwKSB7XG4gICAgICB0aHJvdyBuZXcgRXJyb3IoXCJVUkwgaXMgcmVxdWlyZWRcIik7XG4gICAgfVxuICAgIGNvbnN0IHJlc3BvbnNlID0gYXdhaXQgcG9zdCh0aGlzLmZldGNoLCBgaHR0cHM6Ly9vbGxhbWEuY29tL2FwaS93ZWJfZmV0Y2hgLCB7IC4uLnJlcXVlc3QgfSwgeyBoZWFkZXJzOiB0aGlzLmNvbmZpZy5oZWFkZXJzIH0pO1xuICAgIHJldHVybiBhd2FpdCByZXNwb25zZS5qc29uKCk7XG4gIH1cbn07XG5jb25zdCBicm93c2VyID0gbmV3IE9sbGFtYSQxKCk7XG5cbmV4cG9ydHMuT2xsYW1hID0gT2xsYW1hJDE7XG5leHBvcnRzLmRlZmF1bHQgPSBicm93c2VyO1xuIiwiJ3VzZSBzdHJpY3QnO1xuXG5PYmplY3QuZGVmaW5lUHJvcGVydHkoZXhwb3J0cywgJ19fZXNNb2R1bGUnLCB7IHZhbHVlOiB0cnVlIH0pO1xuXG5jb25zdCBmcyA9IHJlcXVpcmUoJ25vZGU6ZnMnKTtcbmNvbnN0IG5vZGVfcGF0aCA9IHJlcXVpcmUoJ25vZGU6cGF0aCcpO1xuY29uc3QgYnJvd3NlciA9IHJlcXVpcmUoJy4vYnJvd3Nlci5janMnKTtcbnJlcXVpcmUoJ3doYXR3Zy1mZXRjaCcpO1xuXG5mdW5jdGlvbiBfaW50ZXJvcERlZmF1bHRDb21wYXQgKGUpIHsgcmV0dXJuIGUgJiYgdHlwZW9mIGUgPT09ICdvYmplY3QnICYmICdkZWZhdWx0JyBpbiBlID8gZS5kZWZhdWx0IDogZTsgfVxuXG5jb25zdCBmc19fZGVmYXVsdCA9IC8qI19fUFVSRV9fKi9faW50ZXJvcERlZmF1bHRDb21wYXQoZnMpO1xuXG5jbGFzcyBPbGxhbWEgZXh0ZW5kcyBicm93c2VyLk9sbGFtYSB7XG4gIGFzeW5jIGVuY29kZUltYWdlKGltYWdlKSB7XG4gICAgaWYgKHR5cGVvZiBpbWFnZSAhPT0gXCJzdHJpbmdcIikge1xuICAgICAgcmV0dXJuIEJ1ZmZlci5mcm9tKGltYWdlKS50b1N0cmluZyhcImJhc2U2NFwiKTtcbiAgICB9XG4gICAgdHJ5IHtcbiAgICAgIGlmIChmc19fZGVmYXVsdC5leGlzdHNTeW5jKGltYWdlKSkge1xuICAgICAgICBjb25zdCBmaWxlQnVmZmVyID0gYXdhaXQgZnMucHJvbWlzZXMucmVhZEZpbGUobm9kZV9wYXRoLnJlc29sdmUoaW1hZ2UpKTtcbiAgICAgICAgcmV0dXJuIEJ1ZmZlci5mcm9tKGZpbGVCdWZmZXIpLnRvU3RyaW5nKFwiYmFzZTY0XCIpO1xuICAgICAgfVxuICAgIH0gY2F0Y2gge1xuICAgIH1cbiAgICByZXR1cm4gaW1hZ2U7XG4gIH1cbiAgLyoqXG4gICAqIGNoZWNrcyBpZiBhIGZpbGUgZXhpc3RzXG4gICAqIEBwYXJhbSBwYXRoIHtzdHJpbmd9IC0gVGhlIHBhdGggdG8gdGhlIGZpbGVcbiAgICogQHByaXZhdGUgQGludGVybmFsXG4gICAqIEByZXR1cm5zIHtQcm9taXNlPGJvb2xlYW4+fSAtIFdoZXRoZXIgdGhlIGZpbGUgZXhpc3RzIG9yIG5vdFxuICAgKi9cbiAgYXN5bmMgZmlsZUV4aXN0cyhwYXRoKSB7XG4gICAgdHJ5IHtcbiAgICAgIGF3YWl0IGZzLnByb21pc2VzLmFjY2VzcyhwYXRoKTtcbiAgICAgIHJldHVybiB0cnVlO1xuICAgIH0gY2F0Y2gge1xuICAgICAgcmV0dXJuIGZhbHNlO1xuICAgIH1cbiAgfVxuICBhc3luYyBjcmVhdGUocmVxdWVzdCkge1xuICAgIGlmIChyZXF1ZXN0LmZyb20gJiYgYXdhaXQgdGhpcy5maWxlRXhpc3RzKG5vZGVfcGF0aC5yZXNvbHZlKHJlcXVlc3QuZnJvbSkpKSB7XG4gICAgICB0aHJvdyBFcnJvcihcIkNyZWF0aW5nIHdpdGggYSBsb2NhbCBwYXRoIGlzIG5vdCBjdXJyZW50bHkgc3VwcG9ydGVkIGZyb20gb2xsYW1hLWpzXCIpO1xuICAgIH1cbiAgICBpZiAocmVxdWVzdC5zdHJlYW0pIHtcbiAgICAgIHJldHVybiBzdXBlci5jcmVhdGUocmVxdWVzdCk7XG4gICAgfSBlbHNlIHtcbiAgICAgIHJldHVybiBzdXBlci5jcmVhdGUocmVxdWVzdCk7XG4gICAgfVxuICB9XG59XG5jb25zdCBpbmRleCA9IG5ldyBPbGxhbWEoKTtcblxuZXhwb3J0cy5PbGxhbWEgPSBPbGxhbWE7XG5leHBvcnRzLmRlZmF1bHQgPSBpbmRleDtcbiIsImltcG9ydCB7IE9sbGFtYSB9IGZyb20gJ29sbGFtYSdcblxuZXhwb3J0IGFzeW5jIGZ1bmN0aW9uIGxpc3RNb2RlbHModXJsOiBzdHJpbmcpOiBQcm9taXNlPHN0cmluZ1tdPiB7XG4gIGNvbnN0IG9sbGFtYSA9IG5ldyBPbGxhbWEoeyBob3N0OiB1cmwgfSlcbiAgY29uc3QgcmVzcG9uc2UgPSBhd2FpdCBvbGxhbWEubGlzdCgpXG4gIHJldHVybiByZXNwb25zZS5tb2RlbHMubWFwKG0gPT4gbS5uYW1lKVxufVxuXG5leHBvcnQgYXN5bmMgZnVuY3Rpb24gZW1iZWRUZXh0KHVybDogc3RyaW5nLCBtb2RlbDogc3RyaW5nLCB0ZXh0OiBzdHJpbmcpOiBQcm9taXNlPG51bWJlcltdPiB7XG4gIGNvbnN0IG9sbGFtYSA9IG5ldyBPbGxhbWEoeyBob3N0OiB1cmwgfSlcbiAgY29uc3QgcmVzcG9uc2UgPSBhd2FpdCBvbGxhbWEuZW1iZWRkaW5ncyh7XG4gICAgbW9kZWwsXG4gICAgcHJvbXB0OiB0ZXh0LFxuICB9KVxuICByZXR1cm4gcmVzcG9uc2UuZW1iZWRkaW5nXG59XG4iLCJpbXBvcnQgdHlwZSB7IE5vdGVJbmRleCB9IGZyb20gJy4vaW5kZXgnXG5cbmltcG9ydCB7IEJ1ZmZlciB9IGZyb20gJ25vZGU6YnVmZmVyJ1xuaW1wb3J0IHsgY3JlYXRlSGFzaCB9IGZyb20gJ25vZGU6Y3J5cHRvJ1xuaW1wb3J0IHsgY3JlYXRlU2VydmVyIH0gZnJvbSAnbm9kZTpodHRwJ1xuXG5pbXBvcnQgeyBlbWJlZFRleHQgfSBmcm9tICcuL29sbGFtYSdcblxuaW50ZXJmYWNlIE5vdGVTbmFwc2hvdCB7XG4gIHBhdGg6IHN0cmluZ1xuICBjb250ZW50OiBzdHJpbmdcbiAgbXRpbWU6IG51bWJlclxufVxuXG5pbnRlcmZhY2UgU2VydmVyTm90ZUFjY2VzcyB7XG4gIHJlYWROb3RlOiAocGF0aDogc3RyaW5nKSA9PiBQcm9taXNlPE5vdGVTbmFwc2hvdCB8IG51bGw+XG4gIHdyaXRlTm90ZTogKHBhdGg6IHN0cmluZywgY29udGVudDogc3RyaW5nKSA9PiBQcm9taXNlPE5vdGVTbmFwc2hvdCB8IG51bGw+XG4gIHJlaW5kZXhOb3RlOiAocGF0aDogc3RyaW5nKSA9PiBQcm9taXNlPHZvaWQ+XG59XG5cbmNsYXNzIEh0dHBFcnJvciBleHRlbmRzIEVycm9yIHtcbiAgc3RhdHVzOiBudW1iZXJcbiAgcGF5bG9hZDogUmVjb3JkPHN0cmluZywgdW5rbm93bj5cblxuICBjb25zdHJ1Y3RvcihzdGF0dXM6IG51bWJlciwgcGF5bG9hZDogUmVjb3JkPHN0cmluZywgdW5rbm93bj4pIHtcbiAgICBzdXBlcihwYXlsb2FkLmVycm9yIGFzIHN0cmluZylcbiAgICB0aGlzLnN0YXR1cyA9IHN0YXR1c1xuICAgIHRoaXMucGF5bG9hZCA9IHBheWxvYWRcbiAgfVxufVxuXG5mdW5jdGlvbiBjb21wdXRlU2hhMjU2KGNvbnRlbnQ6IHN0cmluZyk6IHN0cmluZyB7XG4gIGNvbnN0IGhhc2ggPSBjcmVhdGVIYXNoKCdzaGEyNTYnKS51cGRhdGUoQnVmZmVyLmZyb20oY29udGVudCwgJ3V0ZjgnKSkuZGlnZXN0KCdoZXgnKVxuICByZXR1cm4gYHNoYTI1Njoke2hhc2h9YFxufVxuXG5mdW5jdGlvbiBzcGxpdExpbmVzKGNvbnRlbnQ6IHN0cmluZyk6IHsgbGluZXM6IHN0cmluZ1tdLCB0cmFpbGluZ05ld2xpbmU6IGJvb2xlYW4gfSB7XG4gIGlmIChjb250ZW50Lmxlbmd0aCA9PT0gMCkge1xuICAgIHJldHVybiB7IGxpbmVzOiBbXSwgdHJhaWxpbmdOZXdsaW5lOiBmYWxzZSB9XG4gIH1cbiAgY29uc3QgdHJhaWxpbmdOZXdsaW5lID0gY29udGVudC5lbmRzV2l0aCgnXFxuJylcbiAgY29uc3QgbGluZXMgPSBjb250ZW50LnNwbGl0KCdcXG4nKVxuICBpZiAodHJhaWxpbmdOZXdsaW5lKSB7XG4gICAgbGluZXMucG9wKClcbiAgfVxuICByZXR1cm4geyBsaW5lcywgdHJhaWxpbmdOZXdsaW5lIH1cbn1cblxuZnVuY3Rpb24gc3BsaXRSZXBsYWNlbWVudChyZXBsYWNlbWVudDogc3RyaW5nKTogc3RyaW5nW10ge1xuICBpZiAocmVwbGFjZW1lbnQubGVuZ3RoID09PSAwKSB7XG4gICAgcmV0dXJuIFtdXG4gIH1cbiAgY29uc3QgbGluZXMgPSByZXBsYWNlbWVudC5zcGxpdCgnXFxuJylcbiAgaWYgKHJlcGxhY2VtZW50LmVuZHNXaXRoKCdcXG4nKSkge1xuICAgIGxpbmVzLnBvcCgpXG4gIH1cbiAgcmV0dXJuIGxpbmVzXG59XG5cbmZ1bmN0aW9uIGpvaW5MaW5lcyhsaW5lczogc3RyaW5nW10sIHRyYWlsaW5nTmV3bGluZTogYm9vbGVhbik6IHN0cmluZyB7XG4gIGNvbnN0IGNvbnRlbnQgPSBsaW5lcy5qb2luKCdcXG4nKVxuICBpZiAodHJhaWxpbmdOZXdsaW5lICYmIGxpbmVzLmxlbmd0aCA+IDApIHtcbiAgICByZXR1cm4gYCR7Y29udGVudH1cXG5gXG4gIH1cbiAgcmV0dXJuIGNvbnRlbnRcbn1cblxuZnVuY3Rpb24gcGFyc2VMaW5lTnVtYmVyKHZhbHVlOiB1bmtub3duLCBrZXk6IHN0cmluZyk6IG51bWJlciB7XG4gIGlmICh0eXBlb2YgdmFsdWUgIT09ICdudW1iZXInIHx8ICFOdW1iZXIuaXNJbnRlZ2VyKHZhbHVlKSkge1xuICAgIHRocm93IG5ldyBIdHRwRXJyb3IoNDAwLCB7IGVycm9yOiBgaW52YWxpZF8ke2tleX1gIH0pXG4gIH1cbiAgcmV0dXJuIHZhbHVlXG59XG5cbmZ1bmN0aW9uIHBhcnNlUmVxdWlyZWRTdHJpbmcodmFsdWU6IHVua25vd24sIGtleTogc3RyaW5nKTogc3RyaW5nIHtcbiAgaWYgKHR5cGVvZiB2YWx1ZSAhPT0gJ3N0cmluZycgfHwgdmFsdWUubGVuZ3RoID09PSAwKSB7XG4gICAgdGhyb3cgbmV3IEh0dHBFcnJvcig0MDAsIHsgZXJyb3I6IGBpbnZhbGlkXyR7a2V5fWAgfSlcbiAgfVxuICByZXR1cm4gdmFsdWVcbn1cblxuZnVuY3Rpb24gcGFyc2VTdHJpbmdGaWVsZCh2YWx1ZTogdW5rbm93biwga2V5OiBzdHJpbmcpOiBzdHJpbmcge1xuICBpZiAodHlwZW9mIHZhbHVlICE9PSAnc3RyaW5nJykge1xuICAgIHRocm93IG5ldyBIdHRwRXJyb3IoNDAwLCB7IGVycm9yOiBgaW52YWxpZF8ke2tleX1gIH0pXG4gIH1cbiAgcmV0dXJuIHZhbHVlXG59XG5cbmZ1bmN0aW9uIHBhcnNlTWFya2Rvd25QYXRoKHZhbHVlOiB1bmtub3duKTogc3RyaW5nIHtcbiAgY29uc3QgcGF0aCA9IHBhcnNlUmVxdWlyZWRTdHJpbmcodmFsdWUsICdwYXRoJylcbiAgaWYgKCFwYXRoLmVuZHNXaXRoKCcubWQnKSkge1xuICAgIHRocm93IG5ldyBIdHRwRXJyb3IoNDAwLCB7IGVycm9yOiAnaW52YWxpZF9wYXRoJyB9KVxuICB9XG4gIHJldHVybiBwYXRoXG59XG5cbmZ1bmN0aW9uIHBhcnNlSnNvbkJvZHkocmF3Qm9keTogc3RyaW5nKTogUmVjb3JkPHN0cmluZywgdW5rbm93bj4ge1xuICB0cnkge1xuICAgIGNvbnN0IGJvZHkgPSBKU09OLnBhcnNlKHJhd0JvZHkpXG4gICAgaWYgKCFib2R5IHx8IHR5cGVvZiBib2R5ICE9PSAnb2JqZWN0JyB8fCBBcnJheS5pc0FycmF5KGJvZHkpKSB7XG4gICAgICB0aHJvdyBuZXcgSHR0cEVycm9yKDQwMCwgeyBlcnJvcjogJ2ludmFsaWRfYm9keScgfSlcbiAgICB9XG4gICAgcmV0dXJuIGJvZHkgYXMgUmVjb3JkPHN0cmluZywgdW5rbm93bj5cbiAgfVxuICBjYXRjaCAoZXJyb3IpIHtcbiAgICBpZiAoZXJyb3IgaW5zdGFuY2VvZiBIdHRwRXJyb3IpIHtcbiAgICAgIHRocm93IGVycm9yXG4gICAgfVxuICAgIHRocm93IG5ldyBIdHRwRXJyb3IoNDAwLCB7IGVycm9yOiAnaW52YWxpZF9qc29uJyB9KVxuICB9XG59XG5cbmV4cG9ydCBjbGFzcyBIdHRwU2VhcmNoU2VydmVyIHtcbiAgcHJpdmF0ZSBzZXJ2ZXI6IGFueVxuICBwcml2YXRlIGluZGV4OiBOb3RlSW5kZXhcbiAgcHJpdmF0ZSBvbGxhbWFVcmw6IHN0cmluZ1xuICBwcml2YXRlIG1vZGVsOiBzdHJpbmdcbiAgcHJpdmF0ZSBub3RlQWNjZXNzOiBTZXJ2ZXJOb3RlQWNjZXNzXG5cbiAgY29uc3RydWN0b3IoaW5kZXg6IE5vdGVJbmRleCwgb2xsYW1hVXJsOiBzdHJpbmcsIG1vZGVsOiBzdHJpbmcsIG5vdGVBY2Nlc3M6IFNlcnZlck5vdGVBY2Nlc3MpIHtcbiAgICB0aGlzLmluZGV4ID0gaW5kZXhcbiAgICB0aGlzLm9sbGFtYVVybCA9IG9sbGFtYVVybFxuICAgIHRoaXMubW9kZWwgPSBtb2RlbFxuICAgIHRoaXMubm90ZUFjY2VzcyA9IG5vdGVBY2Nlc3NcbiAgfVxuXG4gIHB1YmxpYyB1cGRhdGVDb25maWcob2xsYW1hVXJsOiBzdHJpbmcsIG1vZGVsOiBzdHJpbmcpIHtcbiAgICB0aGlzLm9sbGFtYVVybCA9IG9sbGFtYVVybFxuICAgIHRoaXMubW9kZWwgPSBtb2RlbFxuICB9XG5cbiAgcHJpdmF0ZSBhc3luYyBoYW5kbGVSZWFkKGJvZHk6IFJlY29yZDxzdHJpbmcsIHVua25vd24+KTogUHJvbWlzZTxSZWNvcmQ8c3RyaW5nLCB1bmtub3duPj4ge1xuICAgIGNvbnN0IHBhdGggPSBwYXJzZU1hcmtkb3duUGF0aChib2R5LnBhdGgpXG4gICAgY29uc3Qgc25hcHNob3QgPSBhd2FpdCB0aGlzLm5vdGVBY2Nlc3MucmVhZE5vdGUocGF0aClcbiAgICBpZiAoIXNuYXBzaG90KSB7XG4gICAgICB0aHJvdyBuZXcgSHR0cEVycm9yKDQwNCwgeyBlcnJvcjogJ25vdGVfbm90X2ZvdW5kJywgcGF0aCB9KVxuICAgIH1cblxuICAgIGNvbnN0IHsgbGluZXMgfSA9IHNwbGl0TGluZXMoc25hcHNob3QuY29udGVudClcbiAgICByZXR1cm4ge1xuICAgICAgcGF0aDogc25hcHNob3QucGF0aCxcbiAgICAgIGNvbnRlbnQ6IHNuYXBzaG90LmNvbnRlbnQsXG4gICAgICBsaW5lX2NvdW50OiBsaW5lcy5sZW5ndGgsXG4gICAgICBjb250ZW50X2hhc2g6IGNvbXB1dGVTaGEyNTYoc25hcHNob3QuY29udGVudCksXG4gICAgICBtdGltZTogc25hcHNob3QubXRpbWUsXG4gICAgfVxuICB9XG5cbiAgcHJpdmF0ZSBhc3luYyBoYW5kbGVQYXRjaExpbmVzKGJvZHk6IFJlY29yZDxzdHJpbmcsIHVua25vd24+KTogUHJvbWlzZTxSZWNvcmQ8c3RyaW5nLCB1bmtub3duPj4ge1xuICAgIGNvbnN0IHBhdGggPSBwYXJzZU1hcmtkb3duUGF0aChib2R5LnBhdGgpXG4gICAgY29uc3Qgc3RhcnRMaW5lID0gcGFyc2VMaW5lTnVtYmVyKGJvZHkuc3RhcnRfbGluZSwgJ3N0YXJ0X2xpbmUnKVxuICAgIGNvbnN0IGVuZExpbmUgPSBwYXJzZUxpbmVOdW1iZXIoYm9keS5lbmRfbGluZSwgJ2VuZF9saW5lJylcbiAgICBjb25zdCByZXBsYWNlbWVudCA9IHBhcnNlU3RyaW5nRmllbGQoYm9keS5yZXBsYWNlbWVudCwgJ3JlcGxhY2VtZW50JylcbiAgICBjb25zdCBleHBlY3RlZEhhc2ggPSBwYXJzZVJlcXVpcmVkU3RyaW5nKGJvZHkuZXhwZWN0ZWRfaGFzaCwgJ2V4cGVjdGVkX2hhc2gnKVxuXG4gICAgaWYgKHN0YXJ0TGluZSA8IDEgfHwgZW5kTGluZSA8IHN0YXJ0TGluZSkge1xuICAgICAgdGhyb3cgbmV3IEh0dHBFcnJvcig0MDAsIHsgZXJyb3I6ICdpbnZhbGlkX2xpbmVfcmFuZ2UnIH0pXG4gICAgfVxuXG4gICAgY29uc3QgY3VycmVudFNuYXBzaG90ID0gYXdhaXQgdGhpcy5ub3RlQWNjZXNzLnJlYWROb3RlKHBhdGgpXG4gICAgaWYgKCFjdXJyZW50U25hcHNob3QpIHtcbiAgICAgIHRocm93IG5ldyBIdHRwRXJyb3IoNDA0LCB7IGVycm9yOiAnbm90ZV9ub3RfZm91bmQnLCBwYXRoIH0pXG4gICAgfVxuXG4gICAgY29uc3QgY3VycmVudEhhc2ggPSBjb21wdXRlU2hhMjU2KGN1cnJlbnRTbmFwc2hvdC5jb250ZW50KVxuICAgIGlmIChjdXJyZW50SGFzaCAhPT0gZXhwZWN0ZWRIYXNoKSB7XG4gICAgICB0aHJvdyBuZXcgSHR0cEVycm9yKDQwOSwge1xuICAgICAgICBlcnJvcjogJ2hhc2hfbWlzbWF0Y2gnLFxuICAgICAgICBwYXRoLFxuICAgICAgICBleHBlY3RlZF9oYXNoOiBleHBlY3RlZEhhc2gsXG4gICAgICAgIGN1cnJlbnRfaGFzaDogY3VycmVudEhhc2gsXG4gICAgICAgIG10aW1lOiBjdXJyZW50U25hcHNob3QubXRpbWUsXG4gICAgICB9KVxuICAgIH1cblxuICAgIGNvbnN0IHsgbGluZXMsIHRyYWlsaW5nTmV3bGluZSB9ID0gc3BsaXRMaW5lcyhjdXJyZW50U25hcHNob3QuY29udGVudClcbiAgICBpZiAoZW5kTGluZSA+IGxpbmVzLmxlbmd0aCkge1xuICAgICAgdGhyb3cgbmV3IEh0dHBFcnJvcig0MDAsIHsgZXJyb3I6ICdsaW5lX3JhbmdlX291dF9vZl9ib3VuZHMnIH0pXG4gICAgfVxuXG4gICAgY29uc3QgcmVwbGFjZW1lbnRMaW5lcyA9IHNwbGl0UmVwbGFjZW1lbnQocmVwbGFjZW1lbnQpXG4gICAgY29uc3QgdXBkYXRlZExpbmVzID0gW1xuICAgICAgLi4ubGluZXMuc2xpY2UoMCwgc3RhcnRMaW5lIC0gMSksXG4gICAgICAuLi5yZXBsYWNlbWVudExpbmVzLFxuICAgICAgLi4ubGluZXMuc2xpY2UoZW5kTGluZSksXG4gICAgXVxuICAgIGNvbnN0IHVwZGF0ZWRDb250ZW50ID0gam9pbkxpbmVzKHVwZGF0ZWRMaW5lcywgdHJhaWxpbmdOZXdsaW5lKVxuXG4gICAgY29uc3Qgd3JpdGVSZXN1bHQgPSBhd2FpdCB0aGlzLm5vdGVBY2Nlc3Mud3JpdGVOb3RlKHBhdGgsIHVwZGF0ZWRDb250ZW50KVxuICAgIGlmICghd3JpdGVSZXN1bHQpIHtcbiAgICAgIHRocm93IG5ldyBIdHRwRXJyb3IoNDA0LCB7IGVycm9yOiAnbm90ZV9ub3RfZm91bmQnLCBwYXRoIH0pXG4gICAgfVxuICAgIGF3YWl0IHRoaXMubm90ZUFjY2Vzcy5yZWluZGV4Tm90ZShwYXRoKVxuXG4gICAgcmV0dXJuIHtcbiAgICAgIHBhdGg6IHdyaXRlUmVzdWx0LnBhdGgsXG4gICAgICBhcHBsaWVkX3N0YXJ0X2xpbmU6IHN0YXJ0TGluZSxcbiAgICAgIGFwcGxpZWRfZW5kX2xpbmU6IGVuZExpbmUsXG4gICAgICBuZXdfaGFzaDogY29tcHV0ZVNoYTI1Nih1cGRhdGVkQ29udGVudCksXG4gICAgICBuZXdfbGluZV9jb3VudDogdXBkYXRlZExpbmVzLmxlbmd0aCxcbiAgICAgIG10aW1lOiB3cml0ZVJlc3VsdC5tdGltZSxcbiAgICB9XG4gIH1cblxuICBwdWJsaWMgc3RhcnQocG9ydDogbnVtYmVyKSB7XG4gICAgdGhpcy5zZXJ2ZXIgPSBjcmVhdGVTZXJ2ZXIoYXN5bmMgKHJlcSwgcmVzKSA9PiB7XG4gICAgICByZXMuc2V0SGVhZGVyKCdBY2Nlc3MtQ29udHJvbC1BbGxvdy1PcmlnaW4nLCAnKicpXG4gICAgICByZXMuc2V0SGVhZGVyKCdBY2Nlc3MtQ29udHJvbC1BbGxvdy1NZXRob2RzJywgJ0dFVCwgUE9TVCwgUEFUQ0gsIE9QVElPTlMnKVxuICAgICAgcmVzLnNldEhlYWRlcignQWNjZXNzLUNvbnRyb2wtQWxsb3ctSGVhZGVycycsICdDb250ZW50LVR5cGUnKVxuXG4gICAgICBpZiAocmVxLm1ldGhvZCA9PT0gJ09QVElPTlMnKSB7XG4gICAgICAgIHJlcy53cml0ZUhlYWQoMjA0KVxuICAgICAgICByZXMuZW5kKClcbiAgICAgICAgcmV0dXJuXG4gICAgICB9XG5cbiAgICAgIGNvbnN0IHVybCA9IG5ldyBVUkwocmVxLnVybCB8fCAnJywgYGh0dHA6Ly8ke3JlcS5oZWFkZXJzLmhvc3R9YClcbiAgICAgIGNvbnN0IHBhdGhuYW1lID0gdXJsLnBhdGhuYW1lXG5cbiAgICAgIGlmIChyZXEubWV0aG9kID09PSAnR0VUJykge1xuICAgICAgICB0cnkge1xuICAgICAgICAgIGlmIChwYXRobmFtZSA9PT0gJy9ub3Rlcy9yZWFkJykge1xuICAgICAgICAgICAgY29uc3QgZGF0YSA9IHsgcGF0aDogdXJsLnNlYXJjaFBhcmFtcy5nZXQoJ3BhdGgnKSB9XG4gICAgICAgICAgICBjb25zdCBub3RlID0gYXdhaXQgdGhpcy5oYW5kbGVSZWFkKGRhdGEpXG4gICAgICAgICAgICByZXMud3JpdGVIZWFkKDIwMCwgeyAnQ29udGVudC1UeXBlJzogJ2FwcGxpY2F0aW9uL2pzb24nIH0pXG4gICAgICAgICAgICByZXMuZW5kKEpTT04uc3RyaW5naWZ5KG5vdGUpKVxuICAgICAgICAgIH1cbiAgICAgICAgICBlbHNlIHtcbiAgICAgICAgICAgIHJlcy53cml0ZUhlYWQoNDA0KVxuICAgICAgICAgICAgcmVzLmVuZCgpXG4gICAgICAgICAgfVxuICAgICAgICB9XG4gICAgICAgIGNhdGNoIChlcnJvcikge1xuICAgICAgICAgIHRoaXMuaGFuZGxlRXJyb3IocmVzLCBlcnJvcilcbiAgICAgICAgfVxuICAgICAgfVxuICAgICAgZWxzZSBpZiAocmVxLm1ldGhvZCA9PT0gJ1BPU1QnIHx8IHJlcS5tZXRob2QgPT09ICdQQVRDSCcpIHtcbiAgICAgICAgbGV0IGJvZHkgPSAnJ1xuICAgICAgICByZXEub24oJ2RhdGEnLCAoY2h1bmspID0+IHtcbiAgICAgICAgICBib2R5ICs9IGNodW5rLnRvU3RyaW5nKClcbiAgICAgICAgfSlcbiAgICAgICAgcmVxLm9uKCdlbmQnLCBhc3luYyAoKSA9PiB7XG4gICAgICAgICAgdHJ5IHtcbiAgICAgICAgICAgIGNvbnN0IGRhdGEgPSBwYXJzZUpzb25Cb2R5KGJvZHkpXG4gICAgICAgICAgICBpZiAocmVxLm1ldGhvZCA9PT0gJ1BPU1QnICYmIHBhdGhuYW1lID09PSAnL2VtYmVkJykge1xuICAgICAgICAgICAgICBjb25zdCB0ZXh0ID0gcGFyc2VSZXF1aXJlZFN0cmluZyhkYXRhLnRleHQsICd0ZXh0JylcbiAgICAgICAgICAgICAgY29uc3QgdmVjdG9yID0gYXdhaXQgZW1iZWRUZXh0KHRoaXMub2xsYW1hVXJsLCB0aGlzLm1vZGVsLCB0ZXh0KVxuICAgICAgICAgICAgICByZXMud3JpdGVIZWFkKDIwMCwgeyAnQ29udGVudC1UeXBlJzogJ2FwcGxpY2F0aW9uL2pzb24nIH0pXG4gICAgICAgICAgICAgIHJlcy5lbmQoSlNPTi5zdHJpbmdpZnkoeyB2ZWN0b3IgfSkpXG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBlbHNlIGlmIChyZXEubWV0aG9kID09PSAnUE9TVCcgJiYgcGF0aG5hbWUgPT09ICcvc2VhcmNoL3ZlY3RvcicpIHtcbiAgICAgICAgICAgICAgY29uc3QgcmVzdWx0cyA9IHRoaXMuaW5kZXguc2VhcmNoKGRhdGEudmVjdG9yIGFzIG51bWJlcltdLCBkYXRhLmFsbG93bGlzdCBhcyBzdHJpbmdbXSB8IHVuZGVmaW5lZCwgZGF0YS50b3BfbiBhcyBudW1iZXIgfCB1bmRlZmluZWQpXG4gICAgICAgICAgICAgIHJlcy53cml0ZUhlYWQoMjAwLCB7ICdDb250ZW50LVR5cGUnOiAnYXBwbGljYXRpb24vanNvbicgfSlcbiAgICAgICAgICAgICAgcmVzLmVuZChKU09OLnN0cmluZ2lmeSh7IHJlc3VsdHMgfSkpXG4gICAgICAgICAgICB9XG4gICAgICAgICAgICBlbHNlIGlmIChyZXEubWV0aG9kID09PSAnUE9TVCcgJiYgcGF0aG5hbWUgPT09ICcvc2VhcmNoL3RleHQnKSB7XG4gICAgICAgICAgICAgIGNvbnN0IHRleHQgPSBwYXJzZVJlcXVpcmVkU3RyaW5nKGRhdGEudGV4dCwgJ3RleHQnKVxuICAgICAgICAgICAgICBjb25zdCB2ZWN0b3IgPSBhd2FpdCBlbWJlZFRleHQodGhpcy5vbGxhbWFVcmwsIHRoaXMubW9kZWwsIHRleHQpXG4gICAgICAgICAgICAgIGNvbnN0IHJlc3VsdHMgPSB0aGlzLmluZGV4LnNlYXJjaCh2ZWN0b3IsIGRhdGEuYWxsb3dsaXN0IGFzIHN0cmluZ1tdIHwgdW5kZWZpbmVkLCBkYXRhLnRvcF9uIGFzIG51bWJlciB8IHVuZGVmaW5lZClcbiAgICAgICAgICAgICAgcmVzLndyaXRlSGVhZCgyMDAsIHsgJ0NvbnRlbnQtVHlwZSc6ICdhcHBsaWNhdGlvbi9qc29uJyB9KVxuICAgICAgICAgICAgICByZXMuZW5kKEpTT04uc3RyaW5naWZ5KHsgcmVzdWx0cyB9KSlcbiAgICAgICAgICAgIH1cbiAgICAgICAgICAgIGVsc2UgaWYgKHJlcS5tZXRob2QgPT09ICdQQVRDSCcgJiYgcGF0aG5hbWUgPT09ICcvbm90ZXMvcGF0Y2gtbGluZXMnKSB7XG4gICAgICAgICAgICAgIGNvbnN0IHBhdGNoZWQgPSBhd2FpdCB0aGlzLmhhbmRsZVBhdGNoTGluZXMoZGF0YSlcbiAgICAgICAgICAgICAgcmVzLndyaXRlSGVhZCgyMDAsIHsgJ0NvbnRlbnQtVHlwZSc6ICdhcHBsaWNhdGlvbi9qc29uJyB9KVxuICAgICAgICAgICAgICByZXMuZW5kKEpTT04uc3RyaW5naWZ5KHBhdGNoZWQpKVxuICAgICAgICAgICAgfVxuICAgICAgICAgICAgZWxzZSB7XG4gICAgICAgICAgICAgIHJlcy53cml0ZUhlYWQoNDA0KVxuICAgICAgICAgICAgICByZXMuZW5kKClcbiAgICAgICAgICAgIH1cbiAgICAgICAgICB9XG4gICAgICAgICAgY2F0Y2ggKGVycm9yKSB7XG4gICAgICAgICAgICB0aGlzLmhhbmRsZUVycm9yKHJlcywgZXJyb3IpXG4gICAgICAgICAgfVxuICAgICAgICB9KVxuICAgICAgfVxuICAgICAgZWxzZSB7XG4gICAgICAgIHJlcy53cml0ZUhlYWQoNDA1KVxuICAgICAgICByZXMuZW5kKClcbiAgICAgIH1cbiAgICB9KVxuXG4gICAgdGhpcy5zZXJ2ZXIubGlzdGVuKHBvcnQsICcxMjcuMC4wLjEnKVxuICB9XG5cbiAgcHJpdmF0ZSBoYW5kbGVFcnJvcihyZXM6IGFueSwgZXJyb3I6IHVua25vd24pIHtcbiAgICBpZiAoZXJyb3IgaW5zdGFuY2VvZiBIdHRwRXJyb3IpIHtcbiAgICAgIHJlcy53cml0ZUhlYWQoZXJyb3Iuc3RhdHVzLCB7ICdDb250ZW50LVR5cGUnOiAnYXBwbGljYXRpb24vanNvbicgfSlcbiAgICAgIHJlcy5lbmQoSlNPTi5zdHJpbmdpZnkoZXJyb3IucGF5bG9hZCkpXG4gICAgICByZXR1cm5cbiAgICB9XG5cbiAgICBjb25zdCBtZXNzYWdlID0gZXJyb3IgaW5zdGFuY2VvZiBFcnJvciA/IGVycm9yLm1lc3NhZ2UgOiBTdHJpbmcoZXJyb3IpXG4gICAgcmVzLndyaXRlSGVhZCg1MDAsIHsgJ0NvbnRlbnQtVHlwZSc6ICdhcHBsaWNhdGlvbi9qc29uJyB9KVxuICAgIHJlcy5lbmQoSlNPTi5zdHJpbmdpZnkoeyBlcnJvcjogbWVzc2FnZSB9KSlcbiAgfVxuXG4gIHB1YmxpYyBzdG9wKCkge1xuICAgIGlmICh0aGlzLnNlcnZlcikge1xuICAgICAgdGhpcy5zZXJ2ZXIuY2xvc2UoKVxuICAgIH1cbiAgfVxufVxuIiwiZXhwb3J0IGludGVyZmFjZSBWZWN0b3JTZWFyY2hTZXR0aW5ncyB7XG4gIG9sbGFtYVVybDogc3RyaW5nXG4gIG9sbGFtYVRva2VuOiBzdHJpbmdcbiAgZW1iZWRkaW5nTW9kZWw6IHN0cmluZ1xuICBzZXJ2ZXJQb3J0OiBudW1iZXJcbiAgbWluQ2hhcnM6IG51bWJlclxufVxuXG5leHBvcnQgY29uc3QgREVGQVVMVF9TRVRUSU5HUzogVmVjdG9yU2VhcmNoU2V0dGluZ3MgPSB7XG4gIG9sbGFtYVVybDogJ2h0dHA6Ly9sb2NhbGhvc3Q6MTE0MzQnLFxuICBvbGxhbWFUb2tlbjogJycsXG4gIGVtYmVkZGluZ01vZGVsOiAnJyxcbiAgc2VydmVyUG9ydDogNTEzNjIsXG4gIG1pbkNoYXJzOiAxMDAsXG59XG4iLCJpbXBvcnQgdHlwZSB7IEFwcCB9IGZyb20gJ29ic2lkaWFuJ1xuXG5pbXBvcnQgdHlwZSBWZWN0b3JTZWFyY2hQbHVnaW4gZnJvbSAnLi9tYWluJ1xuXG5pbXBvcnQgeyBQbHVnaW5TZXR0aW5nVGFiLCBTZXR0aW5nIH0gZnJvbSAnb2JzaWRpYW4nXG5cbmltcG9ydCB7IGxpc3RNb2RlbHMgfSBmcm9tICcuL29sbGFtYSdcblxuZXhwb3J0IGNsYXNzIFZlY3RvclNlYXJjaFNldHRpbmdzVGFiIGV4dGVuZHMgUGx1Z2luU2V0dGluZ1RhYiB7XG4gIHBsdWdpbjogVmVjdG9yU2VhcmNoUGx1Z2luXG5cbiAgY29uc3RydWN0b3IoYXBwOiBBcHAsIHBsdWdpbjogVmVjdG9yU2VhcmNoUGx1Z2luKSB7XG4gICAgc3VwZXIoYXBwLCBwbHVnaW4pXG4gICAgdGhpcy5wbHVnaW4gPSBwbHVnaW5cbiAgfVxuXG4gIGRpc3BsYXkoKTogdm9pZCB7XG4gICAgY29uc3QgeyBjb250YWluZXJFbCB9ID0gdGhpc1xuXG4gICAgY29udGFpbmVyRWwuZW1wdHkoKVxuXG4gICAgbmV3IFNldHRpbmcoY29udGFpbmVyRWwpXG4gICAgICAuc2V0TmFtZSgnT2xsYW1hIFVSTCcpXG4gICAgICAuc2V0RGVzYygnRW5kcG9pbnQgZm9yIHlvdXIgbG9jYWwgT2xsYW1hIGluc3RhbmNlJylcbiAgICAgIC5hZGRUZXh0KHRleHQgPT4gdGV4dFxuICAgICAgICAuc2V0UGxhY2Vob2xkZXIoJ2h0dHA6Ly9sb2NhbGhvc3Q6MTE0MzQnKVxuICAgICAgICAuc2V0VmFsdWUodGhpcy5wbHVnaW4uc2V0dGluZ3Mub2xsYW1hVXJsKVxuICAgICAgICAub25DaGFuZ2UoYXN5bmMgKHZhbHVlKSA9PiB7XG4gICAgICAgICAgdGhpcy5wbHVnaW4uc2V0dGluZ3Mub2xsYW1hVXJsID0gdmFsdWVcbiAgICAgICAgICBhd2FpdCB0aGlzLnBsdWdpbi5zYXZlU2V0dGluZ3MoKVxuICAgICAgICAgIHRoaXMuZGlzcGxheSgpIC8vIFJlZnJlc2ggdG8gdXBkYXRlIG1vZGVsIGxpc3RcbiAgICAgICAgfSkpXG5cbiAgICBjb25zdCBtb2RlbFNldHRpbmcgPSBuZXcgU2V0dGluZyhjb250YWluZXJFbClcbiAgICAgIC5zZXROYW1lKCdFbWJlZGRpbmcgTW9kZWwnKVxuICAgICAgLnNldERlc2MoJ1NlbGVjdCB0aGUgbW9kZWwgdG8gdXNlIGZvciBlbWJlZGRpbmdzJylcblxuICAgIGxpc3RNb2RlbHModGhpcy5wbHVnaW4uc2V0dGluZ3Mub2xsYW1hVXJsKVxuICAgICAgLnRoZW4oKG1vZGVscykgPT4ge1xuICAgICAgICBtb2RlbFNldHRpbmcuYWRkRHJvcGRvd24oKGRyb3Bkb3duKSA9PiB7XG4gICAgICAgICAgZHJvcGRvd24uYWRkT3B0aW9uKCcnLCAnU2VsZWN0IGEgbW9kZWwnKVxuICAgICAgICAgIG1vZGVscy5mb3JFYWNoKG1vZGVsID0+IGRyb3Bkb3duLmFkZE9wdGlvbihtb2RlbCwgbW9kZWwpKVxuICAgICAgICAgIGRyb3Bkb3duLnNldFZhbHVlKHRoaXMucGx1Z2luLnNldHRpbmdzLmVtYmVkZGluZ01vZGVsKVxuICAgICAgICAgIGRyb3Bkb3duLm9uQ2hhbmdlKGFzeW5jICh2YWx1ZSkgPT4ge1xuICAgICAgICAgICAgdGhpcy5wbHVnaW4uc2V0dGluZ3MuZW1iZWRkaW5nTW9kZWwgPSB2YWx1ZVxuICAgICAgICAgICAgYXdhaXQgdGhpcy5wbHVnaW4uc2F2ZVNldHRpbmdzKClcbiAgICAgICAgICAgIHRoaXMucGx1Z2luLnNlcnZlci51cGRhdGVDb25maWcodGhpcy5wbHVnaW4uc2V0dGluZ3Mub2xsYW1hVXJsLCB2YWx1ZSlcblxuICAgICAgICAgICAgLy8gVHJpZ2dlciByZS1pbmRleCB3YXJuaW5nL2FjdGlvblxuICAgICAgICAgICAgaWYgKHZhbHVlKSB7XG4gICAgICAgICAgICAgIG5ldyBTZXR0aW5nKGNvbnRhaW5lckVsKVxuICAgICAgICAgICAgICAgIC5zZXROYW1lKCdSZS1pbmRleCByZXF1aXJlZCcpXG4gICAgICAgICAgICAgICAgLnNldERlc2MoJ0NoYW5naW5nIHRoZSBtb2RlbCByZXF1aXJlcyBhIGZ1bGwgcmUtaW5kZXggb2YgeW91ciB2YXVsdC4nKVxuICAgICAgICAgICAgICAgIC5hZGRCdXR0b24oYnRuID0+IGJ0blxuICAgICAgICAgICAgICAgICAgLnNldEJ1dHRvblRleHQoJ1JlLWluZGV4IEFsbCcpXG4gICAgICAgICAgICAgICAgICAub25DbGljayhhc3luYyAoKSA9PiB7XG4gICAgICAgICAgICAgICAgICAgIGF3YWl0IHRoaXMucGx1Z2luLnJlaW5kZXhBbGwoKVxuICAgICAgICAgICAgICAgICAgfSkpXG4gICAgICAgICAgICB9XG4gICAgICAgICAgfSlcbiAgICAgICAgfSlcbiAgICAgIH0pXG4gICAgICAuY2F0Y2goKF9lcnIpID0+IHtcbiAgICAgICAgbW9kZWxTZXR0aW5nLnNldERlc2MoJ0Vycm9yIGNvbm5lY3RpbmcgdG8gT2xsYW1hLiBNYWtlIHN1cmUgaXQgaXMgcnVubmluZy4nKVxuICAgICAgfSlcblxuICAgIG5ldyBTZXR0aW5nKGNvbnRhaW5lckVsKVxuICAgICAgLnNldE5hbWUoJ0hUVFAgU2VydmVyIFBvcnQnKVxuICAgICAgLnNldERlc2MoJ1BvcnQgZm9yIHRoZSBsb2NhbCBzZWFyY2ggQVBJJylcbiAgICAgIC5hZGRUZXh0KHRleHQgPT4gdGV4dFxuICAgICAgICAuc2V0UGxhY2Vob2xkZXIoJzUxMzYyJylcbiAgICAgICAgLnNldFZhbHVlKFN0cmluZyh0aGlzLnBsdWdpbi5zZXR0aW5ncy5zZXJ2ZXJQb3J0KSlcbiAgICAgICAgLm9uQ2hhbmdlKGFzeW5jICh2YWx1ZSkgPT4ge1xuICAgICAgICAgIHRoaXMucGx1Z2luLnNldHRpbmdzLnNlcnZlclBvcnQgPSBOdW1iZXIodmFsdWUpXG4gICAgICAgICAgYXdhaXQgdGhpcy5wbHVnaW4uc2F2ZVNldHRpbmdzKClcbiAgICAgICAgfSkpXG5cbiAgICBuZXcgU2V0dGluZyhjb250YWluZXJFbClcbiAgICAgIC5zZXROYW1lKCdNaW5pbXVtIENoYXJhY3RlcnMnKVxuICAgICAgLnNldERlc2MoJ05vdGVzIHNob3J0ZXIgdGhhbiB0aGlzIHdpbGwgYmUgc2tpcHBlZCBkdXJpbmcgaW5kZXhpbmcnKVxuICAgICAgLmFkZFRleHQodGV4dCA9PiB0ZXh0XG4gICAgICAgIC5zZXRQbGFjZWhvbGRlcignMTAwJylcbiAgICAgICAgLnNldFZhbHVlKFN0cmluZyh0aGlzLnBsdWdpbi5zZXR0aW5ncy5taW5DaGFycykpXG4gICAgICAgIC5vbkNoYW5nZShhc3luYyAodmFsdWUpID0+IHtcbiAgICAgICAgICB0aGlzLnBsdWdpbi5zZXR0aW5ncy5taW5DaGFycyA9IE51bWJlcih2YWx1ZSlcbiAgICAgICAgICBhd2FpdCB0aGlzLnBsdWdpbi5zYXZlU2V0dGluZ3MoKVxuICAgICAgICB9KSlcblxuICAgIGNvbnN0IHVzYWdlID0gdGhpcy5wbHVnaW4uaW5kZXguc2l6ZUluQnl0ZXMoKVxuICAgIG5ldyBTZXR0aW5nKGNvbnRhaW5lckVsKVxuICAgICAgLnNldE5hbWUoJ0luZGV4IFN0b3JhZ2UgVXNhZ2UnKVxuICAgICAgLnNldERlc2MoYEN1cnJlbnRseSB1c2luZyAkeyh1c2FnZSAvIDEwMjQgLyAxMDI0KS50b0ZpeGVkKDIpfSBNQiBvbiBkaXNrYClcbiAgICAgIC5hZGRCdXR0b24oYnRuID0+IGJ0blxuICAgICAgICAuc2V0QnV0dG9uVGV4dCgnUmVmcmVzaCBVc2FnZScpXG4gICAgICAgIC5vbkNsaWNrKCgpID0+IHRoaXMuZGlzcGxheSgpKSlcblxuICAgIG5ldyBTZXR0aW5nKGNvbnRhaW5lckVsKVxuICAgICAgLnNldE5hbWUoJ0ZvcmNlIFJlLWluZGV4JylcbiAgICAgIC5zZXREZXNjKCdUcmlnZ2VyIGEgZnVsbCByZS1pbmRleCBvZiB0aGUgdmF1bHQnKVxuICAgICAgLmFkZEJ1dHRvbihidG4gPT4gYnRuXG4gICAgICAgIC5zZXRCdXR0b25UZXh0KCdSZS1pbmRleCBBbGwgTm93JylcbiAgICAgICAgLnNldFdhcm5pbmcoKVxuICAgICAgICAub25DbGljayhhc3luYyAoKSA9PiB7XG4gICAgICAgICAgYXdhaXQgdGhpcy5wbHVnaW4ucmVpbmRleEFsbCgpXG4gICAgICAgIH0pKVxuICB9XG59XG4iLCJpbXBvcnQgdHlwZSB7IFZlY3RvclNlYXJjaFNldHRpbmdzIH0gZnJvbSAnLi9zZXR0aW5ncydcblxuaW1wb3J0IHsgTm90aWNlLCBQbHVnaW4sIFRGaWxlIH0gZnJvbSAnb2JzaWRpYW4nXG5cbmltcG9ydCB7IE5vdGVJbmRleCB9IGZyb20gJy4vaW5kZXgnXG5pbXBvcnQgeyBlbWJlZFRleHQgfSBmcm9tICcuL29sbGFtYSdcbmltcG9ydCB7IEh0dHBTZWFyY2hTZXJ2ZXIgfSBmcm9tICcuL3NlcnZlcidcbmltcG9ydCB7IERFRkFVTFRfU0VUVElOR1MgfSBmcm9tICcuL3NldHRpbmdzJ1xuaW1wb3J0IHsgVmVjdG9yU2VhcmNoU2V0dGluZ3NUYWIgfSBmcm9tICcuL3NldHRpbmdzVGFiJ1xuXG5leHBvcnQgZGVmYXVsdCBjbGFzcyBWZWN0b3JTZWFyY2hQbHVnaW4gZXh0ZW5kcyBQbHVnaW4ge1xuICBzZXR0aW5ncyE6IFZlY3RvclNlYXJjaFNldHRpbmdzXG4gIGluZGV4ITogTm90ZUluZGV4XG4gIHNlcnZlciE6IEh0dHBTZWFyY2hTZXJ2ZXJcblxuICBhc3luYyBvbmxvYWQoKSB7XG4gICAgYXdhaXQgdGhpcy5sb2FkU2V0dGluZ3MoKVxuXG4gICAgdGhpcy5pbmRleCA9IG5ldyBOb3RlSW5kZXgoKVxuICAgIGF3YWl0IHRoaXMubG9hZEluZGV4KClcblxuICAgIHRoaXMuc2VydmVyID0gbmV3IEh0dHBTZWFyY2hTZXJ2ZXIoXG4gICAgICB0aGlzLmluZGV4LFxuICAgICAgdGhpcy5zZXR0aW5ncy5vbGxhbWFVcmwsXG4gICAgICB0aGlzLnNldHRpbmdzLmVtYmVkZGluZ01vZGVsLFxuICAgICAge1xuICAgICAgICByZWFkTm90ZTogYXN5bmMgKHBhdGg6IHN0cmluZykgPT4gdGhpcy5yZWFkTm90ZShwYXRoKSxcbiAgICAgICAgd3JpdGVOb3RlOiBhc3luYyAocGF0aDogc3RyaW5nLCBjb250ZW50OiBzdHJpbmcpID0+IHRoaXMud3JpdGVOb3RlKHBhdGgsIGNvbnRlbnQpLFxuICAgICAgICByZWluZGV4Tm90ZTogYXN5bmMgKHBhdGg6IHN0cmluZykgPT4gdGhpcy5yZWluZGV4Tm90ZShwYXRoKSxcbiAgICAgIH0sXG4gICAgKVxuICAgIHRoaXMuc2VydmVyLnN0YXJ0KHRoaXMuc2V0dGluZ3Muc2VydmVyUG9ydClcblxuICAgIHRoaXMuYWRkU2V0dGluZ1RhYihuZXcgVmVjdG9yU2VhcmNoU2V0dGluZ3NUYWIodGhpcy5hcHAsIHRoaXMpKVxuXG4gICAgdGhpcy5hcHAud29ya3NwYWNlLm9uTGF5b3V0UmVhZHkoKCkgPT4ge1xuICAgICAgdGhpcy5pbmNyZW1lbnRhbEluZGV4KClcbiAgICB9KVxuXG4gICAgdGhpcy5yZWdpc3RlckV2ZW50KFxuICAgICAgdGhpcy5hcHAudmF1bHQub24oJ21vZGlmeScsIGFzeW5jIChmaWxlKSA9PiB7XG4gICAgICAgIGlmIChmaWxlIGluc3RhbmNlb2YgVEZpbGUgJiYgZmlsZS5leHRlbnNpb24gPT09ICdtZCcpIHtcbiAgICAgICAgICBhd2FpdCB0aGlzLmluZGV4RmlsZShmaWxlKVxuICAgICAgICAgIGF3YWl0IHRoaXMuc2F2ZUluZGV4KClcbiAgICAgICAgfVxuICAgICAgfSksXG4gICAgKVxuXG4gICAgdGhpcy5yZWdpc3RlckV2ZW50KFxuICAgICAgdGhpcy5hcHAudmF1bHQub24oJ2NyZWF0ZScsIGFzeW5jIChmaWxlKSA9PiB7XG4gICAgICAgIGlmIChmaWxlIGluc3RhbmNlb2YgVEZpbGUgJiYgZmlsZS5leHRlbnNpb24gPT09ICdtZCcpIHtcbiAgICAgICAgICBhd2FpdCB0aGlzLmluZGV4RmlsZShmaWxlKVxuICAgICAgICAgIGF3YWl0IHRoaXMuc2F2ZUluZGV4KClcbiAgICAgICAgfVxuICAgICAgfSksXG4gICAgKVxuXG4gICAgdGhpcy5yZWdpc3RlckV2ZW50KFxuICAgICAgdGhpcy5hcHAudmF1bHQub24oJ2RlbGV0ZScsIGFzeW5jIChmaWxlKSA9PiB7XG4gICAgICAgIGlmIChmaWxlIGluc3RhbmNlb2YgVEZpbGUpIHtcbiAgICAgICAgICB0aGlzLmluZGV4LmRlbGV0ZShmaWxlLnBhdGgpXG4gICAgICAgICAgYXdhaXQgdGhpcy5zYXZlSW5kZXgoKVxuICAgICAgICB9XG4gICAgICB9KSxcbiAgICApXG5cbiAgICB0aGlzLnJlZ2lzdGVyRXZlbnQoXG4gICAgICB0aGlzLmFwcC52YXVsdC5vbigncmVuYW1lJywgYXN5bmMgKGZpbGUsIG9sZFBhdGgpID0+IHtcbiAgICAgICAgaWYgKGZpbGUgaW5zdGFuY2VvZiBURmlsZSAmJiBmaWxlLmV4dGVuc2lvbiA9PT0gJ21kJykge1xuICAgICAgICAgIHRoaXMuaW5kZXguZGVsZXRlKG9sZFBhdGgpXG4gICAgICAgICAgYXdhaXQgdGhpcy5pbmRleEZpbGUoZmlsZSlcbiAgICAgICAgICBhd2FpdCB0aGlzLnNhdmVJbmRleCgpXG4gICAgICAgIH1cbiAgICAgIH0pLFxuICAgIClcbiAgfVxuXG4gIG9udW5sb2FkKCkge1xuICAgIHRoaXMuc2VydmVyLnN0b3AoKVxuICB9XG5cbiAgYXN5bmMgbG9hZFNldHRpbmdzKCkge1xuICAgIHRoaXMuc2V0dGluZ3MgPSBPYmplY3QuYXNzaWduKHt9LCBERUZBVUxUX1NFVFRJTkdTLCBhd2FpdCB0aGlzLmxvYWREYXRhKCkpXG4gIH1cblxuICBhc3luYyBzYXZlU2V0dGluZ3MoKSB7XG4gICAgYXdhaXQgdGhpcy5zYXZlRGF0YSh0aGlzLnNldHRpbmdzKVxuICB9XG5cbiAgYXN5bmMgbG9hZEluZGV4KCkge1xuICAgIGNvbnN0IGluZGV4UGF0aCA9IHRoaXMuZ2V0SW5kZXhGaWxlUGF0aCgpXG4gICAgaWYgKGF3YWl0IHRoaXMuYXBwLnZhdWx0LmFkYXB0ZXIuZXhpc3RzKGluZGV4UGF0aCkpIHtcbiAgICAgIGNvbnN0IGRhdGEgPSBhd2FpdCB0aGlzLmFwcC52YXVsdC5hZGFwdGVyLnJlYWQoaW5kZXhQYXRoKVxuICAgICAgdGhpcy5pbmRleC5kZXNlcmlhbGl6ZShkYXRhKVxuICAgIH1cbiAgfVxuXG4gIGFzeW5jIHNhdmVJbmRleCgpIHtcbiAgICBjb25zdCBpbmRleFBhdGggPSB0aGlzLmdldEluZGV4RmlsZVBhdGgoKVxuICAgIGF3YWl0IHRoaXMuYXBwLnZhdWx0LmFkYXB0ZXIud3JpdGUoaW5kZXhQYXRoLCB0aGlzLmluZGV4LnNlcmlhbGl6ZSgpKVxuICB9XG5cbiAgZ2V0SW5kZXhGaWxlUGF0aCgpOiBzdHJpbmcge1xuICAgIHJldHVybiBgJHt0aGlzLm1hbmlmZXN0LmRpcn0vaW5kZXguanNvbmBcbiAgfVxuXG4gIHByaXZhdGUgZ2V0TWFya2Rvd25GaWxlKHBhdGg6IHN0cmluZyk6IFRGaWxlIHwgbnVsbCB7XG4gICAgY29uc3QgYWJzdHJhY3RGaWxlID0gdGhpcy5hcHAudmF1bHQuZ2V0QWJzdHJhY3RGaWxlQnlQYXRoKHBhdGgpXG4gICAgaWYgKCEoYWJzdHJhY3RGaWxlIGluc3RhbmNlb2YgVEZpbGUpIHx8IGFic3RyYWN0RmlsZS5leHRlbnNpb24gIT09ICdtZCcpIHtcbiAgICAgIHJldHVybiBudWxsXG4gICAgfVxuICAgIHJldHVybiBhYnN0cmFjdEZpbGVcbiAgfVxuXG4gIGFzeW5jIHJlYWROb3RlKHBhdGg6IHN0cmluZyk6IFByb21pc2U8eyBwYXRoOiBzdHJpbmcsIGNvbnRlbnQ6IHN0cmluZywgbXRpbWU6IG51bWJlciB9IHwgbnVsbD4ge1xuICAgIGNvbnN0IGZpbGUgPSB0aGlzLmdldE1hcmtkb3duRmlsZShwYXRoKVxuICAgIGlmICghZmlsZSkge1xuICAgICAgcmV0dXJuIG51bGxcbiAgICB9XG5cbiAgICBjb25zdCBjb250ZW50ID0gYXdhaXQgdGhpcy5hcHAudmF1bHQucmVhZChmaWxlKVxuICAgIHJldHVybiB7XG4gICAgICBwYXRoOiBmaWxlLnBhdGgsXG4gICAgICBjb250ZW50LFxuICAgICAgbXRpbWU6IGZpbGUuc3RhdC5tdGltZSxcbiAgICB9XG4gIH1cblxuICBhc3luYyB3cml0ZU5vdGUocGF0aDogc3RyaW5nLCBjb250ZW50OiBzdHJpbmcpOiBQcm9taXNlPHsgcGF0aDogc3RyaW5nLCBjb250ZW50OiBzdHJpbmcsIG10aW1lOiBudW1iZXIgfSB8IG51bGw+IHtcbiAgICBjb25zdCBmaWxlID0gdGhpcy5nZXRNYXJrZG93bkZpbGUocGF0aClcbiAgICBpZiAoIWZpbGUpIHtcbiAgICAgIHJldHVybiBudWxsXG4gICAgfVxuXG4gICAgYXdhaXQgdGhpcy5hcHAudmF1bHQubW9kaWZ5KGZpbGUsIGNvbnRlbnQpXG4gICAgY29uc3QgcmVmcmVzaGVkID0gdGhpcy5nZXRNYXJrZG93bkZpbGUocGF0aClcbiAgICBpZiAoIXJlZnJlc2hlZCkge1xuICAgICAgcmV0dXJuIG51bGxcbiAgICB9XG5cbiAgICByZXR1cm4ge1xuICAgICAgcGF0aDogcmVmcmVzaGVkLnBhdGgsXG4gICAgICBjb250ZW50LFxuICAgICAgbXRpbWU6IHJlZnJlc2hlZC5zdGF0Lm10aW1lLFxuICAgIH1cbiAgfVxuXG4gIGFzeW5jIHJlaW5kZXhOb3RlKHBhdGg6IHN0cmluZyk6IFByb21pc2U8dm9pZD4ge1xuICAgIGNvbnN0IGZpbGUgPSB0aGlzLmdldE1hcmtkb3duRmlsZShwYXRoKVxuICAgIGlmICghZmlsZSkge1xuICAgICAgcmV0dXJuXG4gICAgfVxuXG4gICAgYXdhaXQgdGhpcy5pbmRleEZpbGUoZmlsZSlcbiAgICBhd2FpdCB0aGlzLnNhdmVJbmRleCgpXG4gIH1cblxuICBhc3luYyBpbmRleEZpbGUoZmlsZTogVEZpbGUpIHtcbiAgICBpZiAoIXRoaXMuc2V0dGluZ3MuZW1iZWRkaW5nTW9kZWwpXG4gICAgICByZXR1cm5cblxuICAgIGNvbnN0IGNvbnRlbnQgPSBhd2FpdCB0aGlzLmFwcC52YXVsdC5yZWFkKGZpbGUpXG4gICAgaWYgKGNvbnRlbnQubGVuZ3RoIDwgdGhpcy5zZXR0aW5ncy5taW5DaGFycykge1xuICAgICAgdGhpcy5pbmRleC5kZWxldGUoZmlsZS5wYXRoKVxuICAgICAgcmV0dXJuXG4gICAgfVxuXG4gICAgdHJ5IHtcbiAgICAgIGNvbnN0IHZlY3RvciA9IGF3YWl0IGVtYmVkVGV4dChcbiAgICAgICAgdGhpcy5zZXR0aW5ncy5vbGxhbWFVcmwsXG4gICAgICAgIHRoaXMuc2V0dGluZ3MuZW1iZWRkaW5nTW9kZWwsXG4gICAgICAgIGNvbnRlbnQsXG4gICAgICApXG4gICAgICB0aGlzLmluZGV4LnNldChmaWxlLnBhdGgsIHtcbiAgICAgICAgcGF0aDogZmlsZS5wYXRoLFxuICAgICAgICB2ZWN0b3IsXG4gICAgICAgIG10aW1lOiBmaWxlLnN0YXQubXRpbWUsXG4gICAgICB9KVxuICAgIH1cbiAgICBjYXRjaCAoZSkge1xuICAgICAgY29uc29sZS5lcnJvcihgRmFpbGVkIHRvIGVtYmVkICR7ZmlsZS5wYXRofWAsIGUpXG4gICAgfVxuICB9XG5cbiAgYXN5bmMgaW5jcmVtZW50YWxJbmRleCgpIHtcbiAgICBpZiAoIXRoaXMuc2V0dGluZ3MuZW1iZWRkaW5nTW9kZWwpIHtcbiAgICAgIC8vIGVzbGludC1kaXNhYmxlLW5leHQtbGluZSBuby1uZXdcbiAgICAgIG5ldyBOb3RpY2UoJ1ZlY3RvciBTZWFyY2g6IFNlbGVjdCBhbiBlbWJlZGRpbmcgbW9kZWwgaW4gc2V0dGluZ3MgdG8gZW5hYmxlIHNlYXJjaC4nKVxuICAgICAgcmV0dXJuXG4gICAgfVxuXG4gICAgY29uc3QgZmlsZXMgPSB0aGlzLmFwcC52YXVsdC5nZXRNYXJrZG93bkZpbGVzKClcbiAgICBjb25zdCB0b0luZGV4ID0gZmlsZXMuZmlsdGVyKChmKSA9PiB7XG4gICAgICBjb25zdCBlbnRyeSA9IHRoaXMuaW5kZXguZ2V0KGYucGF0aClcbiAgICAgIHJldHVybiAhZW50cnkgfHwgZW50cnkubXRpbWUgPCBmLnN0YXQubXRpbWVcbiAgICB9KVxuXG4gICAgaWYgKHRvSW5kZXgubGVuZ3RoID09PSAwKVxuICAgICAgcmV0dXJuXG5cbiAgICAvLyBlc2xpbnQtZGlzYWJsZS1uZXh0LWxpbmUgbm8tbmV3XG4gICAgbmV3IE5vdGljZShgVmVjdG9yIFNlYXJjaDogVXBkYXRpbmcgaW5kZXggZm9yICR7dG9JbmRleC5sZW5ndGh9IGZpbGVzLi4uYClcbiAgICBsZXQgZG9uZSA9IDBcbiAgICBmb3IgKGNvbnN0IGZpbGUgb2YgdG9JbmRleCkge1xuICAgICAgYXdhaXQgdGhpcy5pbmRleEZpbGUoZmlsZSlcbiAgICAgIGRvbmUrK1xuICAgICAgaWYgKGRvbmUgJSAxMCA9PT0gMCkge1xuICAgICAgICAvLyBlc2xpbnQtZGlzYWJsZS1uZXh0LWxpbmUgbm8tY29uc29sZVxuICAgICAgICBjb25zb2xlLmxvZyhgSW5kZXhlZCAke2RvbmV9LyR7dG9JbmRleC5sZW5ndGh9YClcbiAgICAgIH1cbiAgICB9XG4gICAgYXdhaXQgdGhpcy5zYXZlSW5kZXgoKVxuICAgIC8vIGVzbGludC1kaXNhYmxlLW5leHQtbGluZSBuby1uZXdcbiAgICBuZXcgTm90aWNlKCdWZWN0b3IgU2VhcmNoOiBJbmRleCB1cGRhdGUgY29tcGxldGUuJylcbiAgfVxuXG4gIGFzeW5jIHJlaW5kZXhBbGwoKSB7XG4gICAgaWYgKCF0aGlzLnNldHRpbmdzLmVtYmVkZGluZ01vZGVsKSB7XG4gICAgICAvLyBlc2xpbnQtZGlzYWJsZS1uZXh0LWxpbmUgbm8tbmV3XG4gICAgICBuZXcgTm90aWNlKCdWZWN0b3IgU2VhcmNoOiBTZWxlY3QgYSBtb2RlbCBmaXJzdC4nKVxuICAgICAgcmV0dXJuXG4gICAgfVxuXG4gICAgdGhpcy5pbmRleC5jbGVhcigpXG4gICAgY29uc3QgZmlsZXMgPSB0aGlzLmFwcC52YXVsdC5nZXRNYXJrZG93bkZpbGVzKClcblxuICAgIC8vIGVzbGludC1kaXNhYmxlLW5leHQtbGluZSBuby1uZXdcbiAgICBuZXcgTm90aWNlKGBWZWN0b3IgU2VhcmNoOiBGdWxsIHJlLWluZGV4IHN0YXJ0ZWQgKCR7ZmlsZXMubGVuZ3RofSBmaWxlcykuLi5gKVxuXG4gICAgbGV0IGRvbmUgPSAwXG4gICAgZm9yIChjb25zdCBmaWxlIG9mIGZpbGVzKSB7XG4gICAgICBhd2FpdCB0aGlzLmluZGV4RmlsZShmaWxlKVxuICAgICAgZG9uZSsrXG4gICAgICBpZiAoZG9uZSAlIDEwID09PSAwKSB7XG4gICAgICAgIC8vIGVzbGludC1kaXNhYmxlLW5leHQtbGluZSBuby1jb25zb2xlXG4gICAgICAgIGNvbnNvbGUubG9nKGBSZS1pbmRleGluZyAke2RvbmV9LyR7ZmlsZXMubGVuZ3RofWApXG4gICAgICB9XG4gICAgfVxuXG4gICAgYXdhaXQgdGhpcy5zYXZlSW5kZXgoKVxuICAgIC8vIGVzbGludC1kaXNhYmxlLW5leHQtbGluZSBuby1uZXdcbiAgICBuZXcgTm90aWNlKCdWZWN0b3IgU2VhcmNoOiBGdWxsIHJlLWluZGV4IGNvbXBsZXRlLicpXG4gIH1cbn1cbiIsImltcG9ydCB7IGdldERlZmF1bHRFeHBvcnRGcm9tQ2pzIH0gZnJvbSBcIlx1MDAwMGNvbW1vbmpzSGVscGVycy5qc1wiO1xuaW1wb3J0IHsgX19yZXF1aXJlIGFzIHJlcXVpcmVNYWluIH0gZnJvbSBcIi9Vc2Vycy9hbnRvbmx1L2NvZGUvZHJhZ29uZ2xhc3Mvb2JzaWRpYW4tcGx1Z2luL3NyYy9tYWluLnRzXCI7XG52YXIgbWFpbkV4cG9ydHMgPSByZXF1aXJlTWFpbigpO1xuZXhwb3J0IHsgbWFpbkV4cG9ydHMgYXMgX19tb2R1bGVFeHBvcnRzIH07XG5leHBvcnQgZGVmYXVsdCAvKkBfX1BVUkVfXyovZ2V0RGVmYXVsdEV4cG9ydEZyb21DanMobWFpbkV4cG9ydHMpOyJdLCJuYW1lcyI6WyJIZWFkZXJzIiwiZmV0Y2giLCJicm93c2VyXzEiLCJicm93c2VyIiwicmVxdWlyZSQkMiIsInJlcXVpcmUkJDAiLCJyZXF1aXJlJCQxIiwicmVxdWlyZSQkMyIsIm1haW4iLCJyZXF1aXJlJCQ0IiwicmVxdWlyZSQkNSJdLCJtYXBwaW5ncyI6Ijs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7O0NBQUEsSUFBQSxXQUFBLEdBQUEsRUFBQTtDQUFBLFFBQUEsQ0FBQSxXQUFBLEVBQUE7R0FBQSxTQUFBLEVBQUEsTUFBQTtBQUFBLEVBQUEsQ0FBQTtBQUFBLENBQUEsR0FBQSxHQUFBLFlBQUEsQ0FBQSxXQUFBLENBQUE7QUFNTyxDQUFBLE1BQU0sU0FBQSxDQUFVO0FBQUEsR0FDYixPQUFBLHVCQUF1QyxHQUFBLEVBQUk7QUFBQSxHQUVuRCxXQUFBLEdBQWM7QUFBQSxHQUFBO0FBQUMsR0FFUixHQUFBLENBQUksTUFBYyxLQUFBLEVBQW1CO0tBQzFDLElBQUEsQ0FBSyxPQUFBLENBQVEsR0FBQSxDQUFJLElBQUEsRUFBTSxLQUFLLENBQUE7QUFBQSxHQUFBO0dBR3ZCLE9BQU8sSUFBQSxFQUFjO0FBQzFCLEtBQUEsSUFBQSxDQUFLLE9BQUEsQ0FBUSxPQUFPLElBQUksQ0FBQTtBQUFBLEdBQUE7R0FHbkIsSUFBSSxJQUFBLEVBQXNDO0tBQy9DLE9BQU8sSUFBQSxDQUFLLE9BQUEsQ0FBUSxHQUFBLENBQUksSUFBSSxDQUFBO0FBQUEsR0FBQTtBQUM5QixHQUVPLEtBQUEsR0FBUTtBQUNiLEtBQUEsSUFBQSxDQUFLLFFBQVEsS0FBQSxFQUFNO0FBQUEsR0FBQTtBQUNyQixHQUVPLE1BQUEsR0FBdUI7S0FDNUIsT0FBTyxLQUFBLENBQU0sSUFBQSxDQUFLLElBQUEsQ0FBSyxPQUFBLENBQVEsUUFBUSxDQUFBO0FBQUEsR0FBQTtHQUdsQyxNQUFBLENBQU8sV0FBQSxFQUF1QixTQUFBLEVBQXNCLElBQUEsR0FBZSxFQUFBLEVBQXVDO0FBQy9HLEtBQUEsSUFBSSxVQUFBLEdBQWEsS0FBSyxNQUFBLEVBQU87S0FDN0IsSUFBSSxTQUFBLElBQWEsU0FBQSxDQUFVLE1BQUEsR0FBUyxD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
