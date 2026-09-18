import java.lang.instrument.*;
import java.security.ProtectionDomain;
import org.objectweb.asm.*;

/** Apply the exact game speed helper to the offline native MTR commissioning JVM. */
public final class FlightSpeedR22Agent
{
    public static void premain(String arguments,Instrumentation instrumentation)
    {
        instrumentation.addTransformer(new ClassFileTransformer()
        {
            @Override public byte[] transform(ClassLoader loader,String name,Class<?> type,ProtectionDomain domain,byte[] bytes)
            {
                if(!name.equals("org/mtr/core/data/PathData"))return null;
                ClassReader reader=new ClassReader(bytes);ClassWriter writer=new ClassWriter(reader,ClassWriter.COMPUTE_MAXS);
                reader.accept(new ClassVisitor(Opcodes.ASM9,writer)
                {
                    @Override public MethodVisitor visitMethod(int access,String method,String descriptor,String signature,String[] exceptions)
                    {
                        MethodVisitor original=super.visitMethod(access,method,descriptor,signature,exceptions);
                        if(!method.equals("getSpeedLimitKilometersPerHour")||!descriptor.equals("()J"))return original;
                        return new MethodVisitor(Opcodes.ASM9,original)
                        {
                            @Override public void visitInsn(int opcode)
                            {
                                if(opcode==Opcodes.LRETURN)
                                {super.visitVarInsn(Opcodes.ALOAD,0);super.visitMethodInsn(Opcodes.INVOKESTATIC,"com/projectseele/world/UNFlightSpeedR22","adjust","(JLjava/lang/Object;)J",false);}
                                super.visitInsn(opcode);
                            }
                        };
                    }
                },0);return writer.toByteArray();
            }
        });
    }
}
