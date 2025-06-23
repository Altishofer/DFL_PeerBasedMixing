export const createSSEService = () => {
  let es = null;
  let messageHandler = () => {};

  return {
    initialize: (url, handler) => {
      messageHandler = handler;
      if (es) es.close();
      es = new EventSource(url);
      es.onmessage = (event) => {
        let data = event.data;
        try {
          data = JSON.parse(event.data);
        } catch {}
        messageHandler(data);
      };
      es.onerror = (err) => {
        console.warn('SSE connection error', err);
      };
    },
    disconnect: () => {
      if (es) es.close();
    }
  };
};
