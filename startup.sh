<<<<<<< HEAD
#!/bin/bash

exec python -m streamlit run streamlit_app.py \

  --server.address=0.0.0.0 \

  --server.port="${PORT:-8000}" \

  --server.headless=true \

  --browser.gatherUsageStats=false
=======
#!/bin/bash 
streamlit run streamlit_app.py --server.port=8000 --server.address=0.0.0.0 
>>>>>>> d910a33dfa31be81a3d0714563856a4fc85b0ef4
