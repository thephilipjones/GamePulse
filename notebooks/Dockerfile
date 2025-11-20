# Jupyter notebook environment for GamePulse data analysis
# Use python-3.11 tag for stability
FROM quay.io/jupyter/scipy-notebook:python-3.12

# Metadata
LABEL maintainer="GamePulse" \
      description="Data analysis environment for GamePulse"

# Install additional dependencies using mamba (conda-compatible)
# scipy-notebook already includes pandas, numpy, matplotlib, seaborn
RUN mamba install --yes -c conda-forge \
    sqlalchemy \
    psycopg \
    plotly \
    ipywidgets \
    jupyterlab-git && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

# Install sqlmodel via pip (conda-forge only has v0.0.9, we need v0.0.22+)
RUN pip install --no-cache-dir sqlmodel>=0.0.22

# Set working directory
WORKDIR /home/jovyan/work

# Healthcheck for docker compose
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8888/api || exit 1

# Expose Jupyter port
EXPOSE 8888
