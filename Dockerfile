# From ElasticSearch documentation, you need to have vm.max_map_count=262144
# in order for ElasticSearch to work. Set it by running `sysctl -w vm.max_map_count=262144`
# source: https://www.elastic.co/guide/en/elasticsearch/reference/current/vm-max-map-count.html#vm-max-map-count

FROM kcing/base

# Configure kcing repo
ENV KCING_HOME /opt/kcing
ENV LS_HOME ${LOGSTASH_HOME}

# Copy kcing
RUN mkdir -p ${KCING_HOME}
COPY . ${KCING_HOME}

WORKDIR ${KCING_HOME}
RUN set -x \
 && git remote rm origin \
 && git remote add origin https://github.com/chaws/kcing \
 && pip3 install -r requirements.txt \
 && service elasticsearch start \
 && ./scripts/wait_elasticsearch.sh \
 && ./kcing.py setup_ls \
 && sed -i 's/-Xmx.*/-Xmx8g/' /opt/logstash/config/jvm.options \
 && service logstash start \
 && cp scripts/elk-pre-hooks.sh /usr/local/bin/ \
 && chmod +x /usr/local/bin/elk-pre-hooks.sh \
 && cp scripts/elk-post-hooks.sh /usr/local/bin/ \
 && chmod +x /usr/local/bin/elk-post-hooks.sh


# Our logstash pipelines ports
EXPOSE 5601 9200 8337 8338 8007
VOLUME /var/lib/elasticsearch

CMD ["/usr/local/bin/start.sh"]
