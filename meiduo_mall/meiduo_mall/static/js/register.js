let vm = new Vue({
    el: "#app", // 通过id选择器 找到绑定的html
    //修改vue读取变量的语法
     delimiters: ['[[', ']]'],
    // 数据对象
    data:{
        //v-model
        username: '',
        password: '',
        password2: '',
        mobile: '',
        allow:'',
        //v-show,控制是否展示错误信息，默认为flase不展示
        error_name: false,
        error_password: false,
        error_password2: false,
        error_mobile: false,
        error_allow: false,

        //error_message
        error_name_message: '',
        error_mobile_message: ''

    },
    //绑定事件
    methods:{
        // 校验用户名
        check_username() {
            // 用户名是5-20个字符，[a-zA-Z0-9_-]
            // 定义正则
            let re = /^[a-zA-Z0-9_-]{5,20}$/;
            // 使用正则匹配用户名数据
            if (re.test(this.username)) {
                // 匹配成功，不展示错误提示信息
                this.error_name = false;
            } else {
                // 匹配失败，展示错误提示信息
                this.error_name_message = '请输入5-20个字符的用户名';
                this.error_name = true;
            }

            // 判断用户名是否重复注册
            if (this.error_name == false){ //只有当用户输入的用户名满足条件时才会去判断
                let url = '/usernames/' + this.username +'/count/';
                axios.get(url,{
                    responseType: 'json' // 后端返回的数据类型
                })
                    // 请求成功，从响应体中中取出count的值
                    .then(response =>{
                        if (response.data.count == 1 ){
                           this.error_name_message = '用户名已存在';
                           // 将error_name 的值改为true（展示错误信息)
                           this.error_name = true;
                        }else{
                            this.error_name = false;
                        }

                    })
                    //请示失败 控制台输出错误信息
                    .catch(error =>{
                        console.log(error.response);
                    })

            }
        },
        // 校验密码
        check_password(){
            let re = /^[0-9A-Za-z]{8,20}$/;
            if (re.test(this.password)){
                // 密码验证通过 error_password = flase 不展示错误信息
                this.error_password = false;
            }else{
                this.error_password = true;
            }
        },
        // 校验确认密码
        check_password2() {
            if (this.password != this.password2) {
                this.error_password2 = true;
            } else {
                this.error_password2 = false;
            }
        },
         // 校验手机号
        check_mobile(){
        let re = /^1[3-9]\d{9}$/;
        if(re.test(this.mobile)) {
            this.error_mobile = false;
        } else {
            this.error_mobile_message = '您输入的手机号格式不正确';
            this.error_mobile = true;
            }

        // 判断手机号是否重复注册
        if (this.error_mobile == false){
            let url = '/mobiles/' + this.mobile + '/count/';
            axios.get(url,{
                responseType: 'json'
            })
                .then(response =>{
                // 手机号存在 将error_mobile的值改为 true
                if (response.data.count == 1){
                    this.error_mobile_message = '手机号已存在';
                    this.error_mobile = true;
                }else{
                    this.error_mobile = false;
                }

             })
                .catch(error =>{
                    console.log(error.response)
            })
        }
        },
        // 校验是否勾选协议
        check_allow(){
            if(!this.allow) {
            this.error_allow = true;
        } else {
            this.error_allow = false;
        }

        },
        // 监听表单提交事件
        on_submit(){
            this.check_username();
            this.check_password();
            this.check_password2();
            this.check_mobile();
            this.check_allow();

            if (this.error_name == true || this.error_password == true || this.error_password2 == true|| this.error_mobile == true || this.error_allow == true) {
                // 禁用掉表单的提交事件
                window.event.returnValue = false;
            }
        },
    }
});