# The MIT License (MIT)
#
# Copyright (c) 2017
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

FROM ubuntu:16.04

# Install Ubuntu dependencies
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -yq python python-dev python-pip libssl-dev git

# Install the proxy script
COPY coinhive-stratum-mining-proxy.py /coinhive-stratum-mining-proxy.py

# Install static files
ADD static /static

# Install Python dependencies
COPY requirements.txt /requirements.txt
RUN pip install -v -r /requirements.txt && rm /requirements.txt

# Expose HTTP/WebSocket port
EXPOSE 8892

# Launch the service
ENTRYPOINT ["/coinhive-stratum-mining-proxy.py"]
CMD []
