FROM python:3.7
RUN pip install kopf kubernetes 
COPY handler.py /handler.py
COPY prom-volume.json /
CMD kopf run --standalone /handler.py --verbose 