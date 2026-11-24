(() => {
    const connection = new Promise(resolve => {
        function connect() {
            if (!window.qt?.webChannelTransport) {
                setTimeout(connect, 0);
                return;
            }
            new QWebChannel(window.qt.webChannelTransport, channel => resolve(channel.objects.django));
        }
        connect();
    });
    const webFetch = window.fetch.bind(window);

    Object.defineProperty(document, 'cookie', {
        get: () => window.__bibliotecaCookies || '',
    });

    async function call(target, method, payload, headers) {
        const django = await connection;
        const packed = await new Promise(resolve => {
            django.request(JSON.stringify({ target, method, payload, headers }), resolve);
        });
        const data = JSON.parse(packed);
        window.__bibliotecaCookies = data.cookies;
        return data;
    }

    window.fetch = async (input, init = {}) => {
        const url = new URL(input instanceof Request ? input.url : input, location.href);
        if (url.protocol !== location.protocol || url.host !== location.host) {
            return webFetch(input, init);
        }
        const request = new Request(input instanceof Request ? input : url, init);
        const headers = new Headers(request.headers);
        let payload = '';
        if (init.body instanceof FormData) {
            payload = new URLSearchParams(init.body).toString();
            headers.set('Content-Type', 'application/x-www-form-urlencoded;charset=UTF-8');
        } else if (request.body !== null) {
            payload = await request.text();
        }

        const data = await call(url.pathname + url.search, request.method, payload, Object.fromEntries(headers));
        const empty = request.method === 'HEAD' || [204, 205, 304].includes(data.status);
        return new Response(empty ? null : data.body, { status: data.status, headers: data.headers });
    };

    document.addEventListener('submit', async event => {
        if (event.target.id !== 'loginForm') return;
        event.preventDefault();
        const form = event.target;
        const button = document.getElementById('loginSubmitBtn');
        button.disabled = true;
        try {
            const data = await call('/login/', 'POST', new URLSearchParams(new FormData(form)).toString(), {
                'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
            });
            if (data.headers.location) {
                location.assign(data.headers.location);
            } else {
                let message = document.getElementById('desktopLoginError');
                if (!message) {
                    message = document.createElement('div');
                    message.id = 'desktopLoginError';
                    message.className = 'alert alert-danger';
                    message.setAttribute('role', 'alert');
                    form.before(message);
                }
                message.textContent = data.status >= 500
                    ? 'No se pudo consultar la base de datos.'
                    : 'Usuario o contraseña incorrectos.';
            }
        } finally {
            button.disabled = false;
        }
    }, true);
})();
