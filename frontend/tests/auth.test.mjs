import { test } from "node:test";
import assert from "node:assert/strict";
import React, { act } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createRoot } from "react-dom/client";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { JSDOM } from "jsdom";
import { createServer } from "vite";

async function serverRun(run) {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  });
  try {
    await run(server);
  } finally {
    await server.close();
  }
}
async function domRun(run) {
  const dom = new JSDOM("<div id='root'></div>", {
    url: "http://127.0.0.1:5173/login",
  });
  const previous = {
    window: globalThis.window,
    document: globalThis.document,
    HTMLElement: globalThis.HTMLElement,
    IS_REACT_ACT_ENVIRONMENT: globalThis.IS_REACT_ACT_ENVIRONMENT,
  };
  Object.assign(globalThis, {
    window: dom.window,
    document: dom.window.document,
    HTMLElement: dom.window.HTMLElement,
    IS_REACT_ACT_ENVIRONMENT: true,
  });
  const root = createRoot(document.getElementById("root"));
  try {
    await serverRun(async (server) =>
      run(server, root, document.getElementById("root")),
    );
  } finally {
    await act(async () => root.unmount());
    dom.window.close();
    Object.assign(globalThis, previous);
  }
}
const anonymous = {
  status: "ready",
  user: null,
  error: "",
  accept() {},
  retry() {},
  logout: async () => {},
};

test("private routes redirect anonymous users without rendering workspace data", async () => {
  await domRun(async (server, root, container) => {
    const { default: Protected } = await server.ssrLoadModule(
      "/src/app/auth/ProtectedApp.tsx",
    );
    const { AuthContext } = await server.ssrLoadModule(
      "/src/app/auth/authContext.ts",
    );
    await act(async () =>
      root.render(
        React.createElement(
          AuthContext.Provider,
          { value: anonymous },
          React.createElement(
            MemoryRouter,
            { initialEntries: ["/app/assistant"] },
            React.createElement(
              Routes,
              null,
              React.createElement(Route, {
                path: "/app/*",
                element: React.createElement(Protected),
              }),
              React.createElement(Route, {
                path: "/login",
                element: React.createElement("p", null, "Login screen"),
              }),
            ),
          ),
        ),
      ),
    );
    assert.equal(container.textContent, "Login screen");
    assert.doesNotMatch(container.textContent, /dataset|Computed results/i);
  });
});

test("registration form has password guidance, safe autocomplete and generic errors", async () => {
  await serverRun(async (server) => {
    const { RegisterPage } = await server.ssrLoadModule(
      "/src/app/auth/AuthPage.tsx",
    );
    const { AuthContext } = await server.ssrLoadModule(
      "/src/app/auth/authContext.ts",
    );
    const html = renderToStaticMarkup(
      React.createElement(
        AuthContext.Provider,
        { value: { ...anonymous, error: "Authentication failed." } },
        React.createElement(
          MemoryRouter,
          null,
          React.createElement(RegisterPage),
        ),
      ),
    );
    assert.match(html, /type="password"/);
    assert.match(html, /autoComplete="new-password"/);
    assert.match(html, /minLength="15"/);
    assert.match(html, /role="alert"/);
    assert.match(html, /uppercase, lowercase, a number and a symbol/);
  });
});

test("auth requests use cookies and CSRF in memory with single-flight session restoration", async () => {
  await serverRun(async (server) => {
    const { authApi } = await server.ssrLoadModule("/src/app/auth/authApi.ts");
    const original = globalThis.fetch;
    const calls = [];
    globalThis.fetch = async (url, init) => {
      calls.push({ url, init });
      const session = {
        user: url.endsWith("/session")
          ? null
          : { id: "user-a", email: "alice@example.com" },
        csrf_token: "csrf-only-not-an-auth-token",
      };
      return url.endsWith("/logout")
        ? new Response(null, { status: 204 })
        : new Response(JSON.stringify(session));
    };
    try {
      await Promise.all([authApi.session(), authApi.session()]);
      assert.equal(calls.length, 1);
      await authApi.register("alice@example.com", "Testing-Strong-Password42!");
      const registration = calls[1];
      assert.equal(registration.init.credentials, "include");
      assert.equal(
        registration.init.headers.get("X-CSRF-Token"),
        "csrf-only-not-an-auth-token",
      );
      assert.deepEqual(JSON.parse(registration.init.body), {
        email: "alice@example.com",
        password: "Testing-Strong-Password42!",
      });
      await authApi.logout();
      assert.equal(calls[2].init.credentials, "include");
      assert.equal(calls[2].init.method, "POST");
    } finally {
      globalThis.fetch = original;
    }
  });
});

test("session restoration, expiration and logout clear the authenticated identity", async () => {
  await domRun(async (server, root, container) => {
    const { default: Provider } = await server.ssrLoadModule(
      "/src/app/auth/AuthProvider.tsx",
    );
    const { useAuth } = await server.ssrLoadModule(
      "/src/app/auth/authContext.ts",
    );
    const { authApi } = await server.ssrLoadModule("/src/app/auth/authApi.ts");
    const { sessionExpired } = await server.ssrLoadModule(
      "/src/app/api/http.ts",
    );
    authApi.session = async () => ({
      user: { id: "a", email: "alice@example.com" },
      csrf_token: "test",
    });
    let logoutCalls = 0;
    authApi.logout = async () => {
      logoutCalls += 1;
    };
    function Probe() {
      const auth = useAuth();
      return React.createElement(
        "div",
        null,
        auth.user?.email || "Anonymous",
        React.createElement(
          "button",
          { onClick: () => void auth.logout() },
          "Logout",
        ),
      );
    }
    await act(async () =>
      root.render(
        React.createElement(Provider, null, React.createElement(Probe)),
      ),
    );
    assert.match(container.textContent, /alice@example.com/);
    await act(async () => container.querySelector("button").click());
    assert.equal(logoutCalls, 1);
    assert.doesNotMatch(container.textContent, /alice@example.com/);
    await act(async () => sessionExpired());
    assert.match(container.textContent, /Anonymous/);
  });
});

test("session restoration failures expose retry without granting access", async () => {
  await domRun(async (server, root, container) => {
    const { default: Provider } = await server.ssrLoadModule(
      "/src/app/auth/AuthProvider.tsx",
    );
    const { useAuth } = await server.ssrLoadModule(
      "/src/app/auth/authContext.ts",
    );
    const { authApi } = await server.ssrLoadModule("/src/app/auth/authApi.ts");
    let attempts = 0;
    authApi.session = async () => {
      attempts += 1;
      if (attempts === 1) throw new Error("network");
      return { user: null, csrf_token: "test" };
    };
    function Probe() {
      const auth = useAuth();
      return React.createElement(
        "div",
        null,
        auth.status,
        auth.error,
        React.createElement("button", { onClick: auth.retry }, "Retry"),
      );
    }
    await act(async () =>
      root.render(
        React.createElement(Provider, null, React.createElement(Probe)),
      ),
    );
    assert.match(container.textContent, /could not be restored/);
    await act(async () => container.querySelector("button").click());
    assert.match(container.textContent, /ready/);
    assert.doesNotMatch(container.textContent, /could not be restored/);
  });
});

test("dataset exports reauthorize through the API with cookies and CSRF", async () => {
  await serverRun(async (server) => {
    const { datasetsApi } = await server.ssrLoadModule(
      "/src/app/api/datasetsApi.ts",
    );
    const { setCsrfToken } = await server.ssrLoadModule("/src/app/api/http.ts");
    setCsrfToken("test-csrf");
    const original = globalThis.fetch;
    globalThis.fetch = async (url, init) => {
      assert.match(url, /\/api\/datasets\/owned-dataset\/export$/);
      assert.equal(init.credentials, "include");
      assert.equal(init.headers.get("X-CSRF-Token"), "test-csrf");
      assert.deepEqual(JSON.parse(init.body), {
        columns: ["amount"],
        limit: 25,
      });
      return new Response('"amount"\r\n"35"\r\n', {
        headers: { "Content-Type": "text/csv" },
      });
    };
    try {
      const blob = await datasetsApi.export("owned-dataset", {
        columns: ["amount"],
        limit: 25,
      });
      assert.equal(await blob.text(), '"amount"\r\n"35"\r\n');
    } finally {
      globalThis.fetch = original;
    }
  });
});
