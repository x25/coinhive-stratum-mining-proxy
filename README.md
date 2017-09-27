# CoinHive Stratum Mining Proxy

A proof of concept of web mining using [CoinHive](https://coin-hive.com/) JavaScript Mining library on a custom stratum XMR pool.

## Installation

Docker:

```bash
$ git clone git@github.com:x25/coinhive-stratum-mining-proxy.git .
$ docker build -t coinhive-stratum-mining-proxy .
$ docker run -p 8892:8892 coinhive-stratum-mining-proxy <stratum tcp host> <stratum tcp port>
```

eg:

```bash
$ docker run -p 8892:8892 coinhive-stratum-mining-proxy xmr-eu1.nanopool.org 14444
```

Linux/Mac:

```bash
$ git clone git@github.com:x25/coinhive-stratum-mining-proxy.git .
$ pip install -v -r requirements.txt
$ python coinhive-stratum-mining-proxy.py <stratum tcp host> <stratum tcp port>
```

## Usage

1. Install and Run `coinhive-stratum-mining-proxy`
2. Load the Coinhive Miner

```html
<script src="https://coin-hive.com/lib/coinhive.min.js"></script>
```

3. Change the `CoinHive.CONFIG.WEBSOCKET_SHARDS` config variable:

```html
<script>
CoinHive.CONFIG.WEBSOCKET_SHARDS = [["ws://localhost:8892/proxy"]];
</script>
```

4. Start Mining

```html
<script>
var miner = new CoinHive.Anonymous('YOUR_WALLET_ADDRESS');
miner.start();
</script>
```
or

```html
<script>
var miner = new CoinHive.User('YOUR_WALLET_ADDRESS', 'YOUR_WORKER_NAME');
miner.start();
</script>
```

5. Profit!

## Demo

Setup and run `coinhive-stratum-mining-proxy` with `xmr-eu1.nanopool.org 14444` parameters and open http://localhost:8892 in your browser for live demo.

## License
MIT
