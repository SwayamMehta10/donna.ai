# import logging
# import os
# from datetime import datetime

# def init_logger(unique_code: str):
#     if not logging.root.handlers:
#         log_file_name = f"{unique_code}_{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"

#         log_dir_path = os.path.join(os.getcwd(), "logs")
#         os.makedirs(log_dir_path, exist_ok=True)

#         log_file_path = os.path.join(log_dir_path, log_file_name)

#         logging.basicConfig(
#             filename=log_file_path,
#             level=logging.INFO,
#             format="[%(asctime)s] %(lineno)d %(name)s - %(levelname)s - %(message)s"
#         )
#         ch = logging.StreamHandler()
#         ch.setLevel(logging.INFO)
#         ch.setFormatter(logging.Formatter("[%(asctime)s] %(lineno)d %(name)s - %(levelname)s - %(message)s"))
#         logging.getLogger().addHandler(ch)
#     return "logger initialized"

import logging
import os
from datetime import datetime

log_file_name = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"

log_dir_path = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir_path, exist_ok=True)

log_file_path = os.path.join(log_dir_path, log_file_name)

logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="[%(asctime)s] %(lineno)d %(name)s - %(levelname)s - %(message)s"
)

