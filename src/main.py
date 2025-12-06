# from langchain_openai import ChatOpenAI
# from langchain.agents import create_agent
# from langchain.messages import HumanMessage
# from langchain_google_genai import ChatGoogleGenerativeAI
# import os
# from tools.computer_use.AgentS.runner import run_computer_use_with_query

# os.environ["GOOGLE_API_KEY"] = "AIzaSyAWtjKoVhYlYCElHVk6Xt75G5RnPkDUQvM"

# system_prompt = """
# Bạn là một trợ lý hỗ trợ lên kế hoạch và kiểm tra tiến độ. Nhiệm vụ của bạn là nhận yêu cầu từ người dùng, yêu cầu này là một tác vụ tự động hóa trên máy tính, sau đó lên kế hoạch chi tiết theo từng bước bằng tiếng anh từ yêu cầu đó sao cho một agent computer use khác dễ hiểu và thực hiện theo. Ví dụ:
# Step 1. Step 2...
# Chỉ được trả về như mẫu trên, không trả lời thêm gì khác, giữa các step không được có dấu xuống dòng. Lưu ý khi lên kế hoạch: màn hình máy tính chưa mở ứng dụng nào cả, phải lên kế hoạch chi tiết từ đầu.
# """

# #tools = [computer_use]

# def init_agent():
#     model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, convert_system_message_to_human=True)
#     agent = create_agent(
#         model=model,
#         #tools=tools,
#         system_prompt=system_prompt,
#     )
#     return agent

# agent = init_agent()

# # while True:
# #     q = input("\nUser: ")
# #     if q.lower() in ["exit", "quit"]:
# #         break

# #     result = agent.invoke(
# #         {
# #             "messages": [{"role":"user", "content":q}]
# #         }
# #     )

# #     print(result)
# print("=== Planner Agent ===")

# while True:
#     q = input("\nUser: ")
#     if q.lower() in ["exit", "quit"]:
#         break

#     plan_output = agent.invoke({
#         "messages": [{"role":"user", "content": q}]
#     })

#     plan_text = plan_output["messages"][1].content
#     # print("\n=== Full Plan ===")
#     # print(plan_text)

#     steps = []
#     for part in plan_text.split("Step "):
#         part = part.strip()
#         if part and part[0].isdigit():
#             step_text = part.split(". ")[1]
#             steps.append(step_text)

#     print("\n=== Executing Steps Sequentially ===")
#     for s in steps:
#         print(f"\nExecuting: {s}")

#         result = run_computer_use_with_query(s)
#         print(result)

#         if "ERROR" in result or "failed" in result.lower():
#             print("⛔ Step failed — stopping.")
#             break

from agents.planner import Planner

engine_params = {
    "engine_type": "gemini",
    "model": "gemini-2.5-flash",
    "base_url": "https://generativelanguage.googleapis.com/v1beta",
    "api_key": "AIzaSyAWtjKoVhYlYCElHVk6Xt75G5RnPkDUQvM",
    "temperature": None,
}

agent = Planner(engine_params)

q = input("\nUser: ")

print(agent.plan_predict(q))